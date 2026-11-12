//! Stream GENESIS v3-compatible *logical* entities as JSON Lines.
//! This is an intermediate interoperability format, NOT a Parquet implementation.
//! Each line: {"entity":"...", "row":{...}}. Output order is deterministic.
//! No entire-dataset collection is held in memory.
use super::{stable_seed, student_id, Catalog};
use crate::rng::PythonRandom;
use serde_json::{json, Value};
use std::io::{self, Write};

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
        if !(1..=2000).contains(&self.students) {
            return Err("pilot JSONL generator supports 1..2000 students".into());
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

pub fn generate<W: Write>(writer: &mut W, catalog: &Catalog, cfg: Config) -> Result<(), String> {
    cfg.validate()?;
    let mut grades: Vec<_> = catalog.grades.iter().collect();
    grades.sort_by_key(|grade| grade.grade_level);

    // Equivalent to school_rows() in epa.genesis.v3.
    for (offset, grade) in grades.iter().enumerate() {
        let year = cfg.start_year + offset as u32;
        for school in 1..=cfg.school_count {
            for section in 1..=cfg.classes_per_grade {
                let class_id = format!("C{year}-{}-S{school:02}-T{section:02}", grade.grade_level);
                write_row(writer, "classes", json!({
                    "class_id": class_id,
                    "school_id": format!("SCHOOL{school:03}"),
                    "academic_year": year,
                    "grade_level": grade.grade_level,
                })).map_err(|e| e.to_string())?;
                for subject in &grade.subjects {
                    write_row(writer, "subject_offerings", json!({
                        "offering_id": format!("{class_id}-{}", subject.id),
                        "class_id": class_id,
                        "subject_id": subject.id,
                        "knowledge_area": subject.area,
                    })).map_err(|e| e.to_string())?;
                }
            }
        }
    }

    let seed_text = cfg.seed.to_string();
    for number in 1..=cfg.students {
        let student = student_id(number);
        write_row(writer, "students", json!({
            "student_id": student, "data_classification": "SYNTHETIC"
        })).map_err(|e| e.to_string())?;

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
            write_row(writer, "enrollments", json!({
                "enrollment_id": enrollment_id, "student_id": student,
                "class_id": class_id, "academic_year": year,
                "grade_level": grade.grade_level, "status": "ENROLLED"
            })).map_err(|e| e.to_string())?;

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
                    write_row(writer, "period_records", json!({
                        "enrollment_id": enrollment_id, "student_id": student,
                        "class_id": class_id, "academic_year": year,
                        "grade_level": grade.grade_level, "subject_id": subject.id,
                        "knowledge_area": subject.area, "term": term,
                        "assessment_grade": score, "scheduled_sessions": sessions,
                        "present_sessions": present, "absences_total": absences,
                        "absences_excused": excused, "absences_unexcused": absences - excused,
                        "attendance_rate": rounded(present as f64 / sessions as f64, 6),
                        "data_classification": "SYNTHETIC"
                    })).map_err(|e| e.to_string())?;
                }
            }
        }
    }
    Ok(())
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
}
