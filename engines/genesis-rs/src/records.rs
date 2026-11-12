//! Stream GENESIS v3-compatible *logical* entities as JSON Lines.
//! This is an intermediate interoperability format, NOT a Parquet implementation.
//! Each line: {"entity":"...", "row":{...}}. Output order is deterministic.
//! No entire-dataset collection is held in memory.
use super::{stable_seed, student_id, Catalog};
use crate::rng::PythonRandom;
use serde::Serialize;
use serde_json::{json, Value};
use std::io::{self, Write};


#[derive(Clone, Debug, Serialize)]
pub struct PeriodRecord {
    pub enrollment_id: String,
    pub student_id: String,
    pub class_id: String,
    pub academic_year: u32,
    pub grade_level: u32,
    pub subject_id: String,
    pub knowledge_area: String,
    pub term: u32,
    pub assessment_grade: f64,
    pub scheduled_sessions: u32,
    pub present_sessions: u32,
    pub absences_total: u32,
    pub absences_excused: u32,
    pub absences_unexcused: u32,
    pub attendance_rate: f64,
    pub data_classification: &'static str,
}

pub enum GeneratedRow {
    Json(&'static str, Value),
    Period(PeriodRecord),
}

const PERIODS: [u32; 4] = [1, 2, 3, 4];
const AREAS: [&str; 4] = ["MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS"];

#[derive(Clone, Copy)]
pub struct Config {
    pub students: u64,
    pub seed: u64,
    pub start_year: u32,
    pub school_count: u32,
    pub classes_per_grade: u32,
}

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if !(1..=100_000).contains(&self.students) {
            return Err("GENESIS Rust supports 1..100000 students".into());
        }
        if !(2000..=2100).contains(&self.start_year) {
            return Err("start_year must be 2000..2100".into());
        }
        if !(1..=20).contains(&self.school_count) || !(1..=20).contains(&self.classes_per_grade) {
            return Err("school_count and classes_per_grade must be 1..20".into());
        }
        Ok(())
    }
}

fn rounded(v: f64, decimals: i32) -> f64 {
    // CPython round ties-to-even. Rare floating-point edge cases require
    // cross-runtime comparison; do not claim bit-identical floats yet.
    let scale = 10f64.powi(decimals);
    (v * scale).round_ties_even() / scale
}
fn bounded(value: f64, lo: f64, hi: f64) -> f64 {
    value.max(lo).min(hi)
}
fn write_row<W: Write>(writer: &mut W, entity: &str, row: Value) -> io::Result<()> {
    serde_json::to_writer(&mut *writer, &json!({"entity": entity, "row": row}))
        .map_err(io::Error::other)?;
    writer.write_all(b"\n")
}

/// Emit typed period records without allocating JSON values on the native hot path.
pub fn generate_typed_rows<F>(catalog: &Catalog, cfg: Config, mut emit: F) -> Result<(), String>
where
    F: FnMut(GeneratedRow) -> Result<(), String>,
{
    cfg.validate()?;
    let mut grades: Vec<_> = catalog.grades.iter().collect();
    grades.sort_by_key(|grade| grade.grade_level);

    // Equivalent to school_rows() in epa.genesis.v3.
    for (offset, grade) in grades.iter().enumerate() {
        let year = cfg.start_year + offset as u32;
        for school in 1..=cfg.school_count {
            for section in 1..=cfg.classes_per_grade {
                let class_id = format!("C{year}-{}-S{school:02}-T{section:02}", grade.grade_level);
                emit(GeneratedRow::Json("classes", json!({
                    "class_id": class_id,
                    "school_id": format!("SCHOOL{school:03}"),
                    "academic_year": year,
                    "grade_level": grade.grade_level,
                })))?;
                for subject in &grade.subjects {
                    emit(GeneratedRow::Json("subject_offerings", json!({
                        "offering_id": format!("{class_id}-{}", subject.id),
                        "class_id": class_id,
                        "subject_id": subject.id,
                        "knowledge_area": subject.area,
                    })))?;
                }
            }
        }
    }

    let seed_text = cfg.seed.to_string();
    for number in 1..=cfg.students {
        let student = student_id(number);
        emit(GeneratedRow::Json("students", json!({
            "student_id": student, "data_classification": "SYNTHETIC"
        })))?;

        let profile_seed = stable_seed(&[seed_text.as_str(), student.as_str(), "profile"]);
        let mut profile_rng = PythonRandom::seeded(profile_seed);
        let mut strengths = [0f64; 4];
        for entry in &mut strengths {
            *entry = profile_rng.uniform(-1.65, 1.65);
        }
        let baseline = profile_rng.uniform(-0.7, 0.7);
        let trend = profile_rng.uniform(-0.27, 0.27);
        let attendance_propensity = profile_rng.uniform(0.78, 0.985);

        for (year_index, grade) in grades.iter().enumerate() {
            let year = cfg.start_year + year_index as u32;
            let year_text = year.to_string();
            let school = 1 + (number - 1) % cfg.school_count as u64;
            let section_seed = stable_seed(&[seed_text.as_str(), student.as_str(), year_text.as_str(), "section"]);
            let section = 1 + (section_seed % cfg.classes_per_grade as u64);
            let class_id = format!("C{year}-{}-S{school:02}-T{section:02}", grade.grade_level);
            let enrollment_id = format!("{student}-{year}");
            emit(GeneratedRow::Json("enrollments", json!({
                "enrollment_id": enrollment_id, "student_id": student,
                "class_id": class_id, "academic_year": year,
                "grade_level": grade.grade_level, "status": "ENROLLED"
            })))?;

            for subject in &grade.subjects {
                let subject_seed = stable_seed(&[seed_text.as_str(), student.as_str(), subject.id.as_str(), "longitudinal"]);
                let bias = PythonRandom::seeded(subject_seed).uniform(-0.48, 0.48);
                let area = AREAS.iter().position(|area| *area == subject.area)
                    .ok_or_else(|| format!("unknown knowledge area {}", subject.area))?;
                for term in PERIODS {
                    let term_text = term.to_string();
                    let record_seed = stable_seed(&[
                        seed_text.as_str(), student.as_str(), year_text.as_str(),
                        subject.id.as_str(), term_text.as_str(),
                    ]);
                    let mut rng = PythonRandom::seeded(record_seed);
                    let raw_grade = 6.1 + baseline + strengths[area] + bias
                        + trend * (year_index as f64 + (term as f64 - 1.0) / 4.0)
                        + rng.gauss(0.0, 0.95);
                    let score = rounded(bounded(raw_grade, 0.0, 10.0), 2);
                    let sessions = rng.randint(16, 25);
                    let probability = bounded(
                        attendance_propensity + rng.gauss(0.0, 0.065)
                            - (5.0 - score).max(0.0) * 0.009,
                        0.30, 1.0,
                    );
                    let mut present = 0;
                    for _ in 0..sessions {
                        if rng.random() < probability { present += 1; }
                    }
                    let absences = sessions - present;
                    let mut excused = 0;
                    for _ in 0..absences {
                        if rng.random() < 0.23 { excused += 1; }
                    }
                    emit(GeneratedRow::Period(PeriodRecord {
                        enrollment_id: enrollment_id.clone(),
                        student_id: student.clone(),
                        class_id: class_id.clone(),
                        academic_year: year,
                        grade_level: grade.grade_level,
                        subject_id: subject.id.clone(),
                        knowledge_area: subject.area.clone(),
                        term,
                        assessment_grade: score,
                        scheduled_sessions: sessions,
                        present_sessions: present,
                        absences_total: absences,
                        absences_excused: excused,
                        absences_unexcused: absences - excused,
                        attendance_rate: rounded(present as f64 / sessions as f64, 6),
                        data_classification: "SYNTHETIC",
                    }))?;
                }
            }
        }
    }
    Ok(())
}



pub fn generate_rows<F>(catalog: &Catalog, cfg: Config, mut emit: F) -> Result<(), String>
where
    F: FnMut(&str, Value) -> Result<(), String>,
{
    generate_typed_rows(catalog, cfg, |row| match row {
        GeneratedRow::Json(entity, value) => emit(entity, value),
        GeneratedRow::Period(record) => {
            let value = serde_json::to_value(record).map_err(|error| error.to_string())?;
            emit("period_records", value)
        }
    })
}

pub fn generate<W: Write>(writer: &mut W, catalog: &Catalog, cfg: Config) -> Result<(), String> {
    generate_rows(catalog, cfg, |entity, row| {
        write_row(writer, entity, row).map_err(|error| error.to_string())
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::load_catalog;
    use std::path::Path;

    #[test]
    fn one_student_has_expected_entities() {
        let (catalog, _) = load_catalog(Path::new("../../examples/atlas.demo.json"))
            .or_else(|_| load_catalog(Path::new("examples/atlas.demo.json")))
            .expect("demo catalog in repo");
        let mut output = Vec::new();
        generate(&mut output, &catalog, Config {
            students: 1, seed: 20261029, start_year: 2020,
            school_count: 2, classes_per_grade: 3,
        }).expect("generate one student");
        let mut counts = std::collections::HashMap::new();
        for line in output.split(|byte| *byte == b'\n').filter(|l| !l.is_empty()) {
            let value: Value = serde_json::from_slice(line).unwrap();
            *counts.entry(value["entity"].as_str().unwrap().to_string()).or_insert(0usize) += 1;
        }
        assert_eq!(counts["students"], 1);
        assert_eq!(counts["classes"], 42);
        assert_eq!(counts["enrollments"], 7);
        assert_eq!(counts["subject_offerings"], 324);
        assert_eq!(counts["period_records"], 216);
    }

    #[test]
    fn rejects_invalid_config() {
        let invalid = Config { students: 0, seed: 42, start_year: 2020,
            school_count: 2, classes_per_grade: 3 };
        assert!(invalid.validate().is_err());
    }
    #[test]
    fn scale_config_accepts_100k_and_rejects_excess() {
        let base = Config {
            students: 100_000, seed: 42, start_year: 2020,
            school_count: 2, classes_per_grade: 3,
        };
        assert!(base.validate().is_ok());
        assert!(Config { students: 100_001, ..base }.validate().is_err());
        assert!(Config { students: 0, ..base }.validate().is_err());
    }
    #[test]
    fn callback_matches_legacy_jsonl_across_seeds() {
        let (catalog, _) = load_catalog(Path::new("../../examples/atlas.demo.json"))
            .or_else(|_| load_catalog(Path::new("examples/atlas.demo.json")))
            .expect("demo catalog");
        for seed in [1, 42, 20261029] {
            let cfg = Config {
                students: 3, seed, start_year: 2020,
                school_count: 2, classes_per_grade: 3,
            };
            let mut jsonl = Vec::new();
            generate(&mut jsonl, &catalog, cfg).expect("legacy JSONL");
            let mut rows = Vec::new();
            generate_rows(&catalog, cfg, |entity, row| {
                rows.push(serde_json::json!({"entity": entity, "row": row}));
                Ok(())
            }).expect("direct callback");
            let old: Vec<Value> = jsonl.split(|b| *b == b'\n')
                .filter(|line| !line.is_empty())
                .map(|line| serde_json::from_slice(line).unwrap())
                .collect();
            assert_eq!(old, rows, "seed={seed}");
            assert_eq!(rows.len(), 42 + 324 + 3 * (1 + 7 + 216));
        }
    }

}
