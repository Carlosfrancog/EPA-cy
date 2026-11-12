//! GENESIS Rust (stage 1): ATLAS validation and Python-compatible stable seeds.
//! No synthetic grades or Parquet output in this stage.
mod rng;
mod records;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, env, fs, path::Path, process};

#[derive(Debug, Deserialize)]
struct Catalog {
    schema_version: String,
    curriculum_type: String,
    source: Source,
    grades: Vec<Grade>,
}
#[derive(Debug, Deserialize)]
struct Source {
    source_label: String,
    reference_url: String,
}
#[derive(Debug, Deserialize)]
struct Grade {
    grade_level: u32,
    subjects: Vec<Subject>,
}
#[derive(Debug, Deserialize)]
struct Subject {
    id: String,
    area: String,
    #[serde(default)]
    bncc_skill_codes: Vec<String>,
}
#[derive(Debug, Serialize)]
struct Inspection {
    schema_version: &'static str,
    catalog_sha256: String,
    generator_seed: u64,
    students: u64,
    classes: u64,
    enrollments: u64,
    subject_offerings: u64,
    period_records: u64,
    terms_per_year: u64,
    first_student_id: String,
    note: &'static str,
}
fn hex_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
/// Matches Python: int.from_bytes(sha256("|".join(map(str, parts)).encode()).digest()[:8], "big")
fn stable_seed(parts: &[&str]) -> u64 {
    let digest = Sha256::digest(parts.join("|").as_bytes());
    u64::from_be_bytes(digest[..8].try_into().expect("SHA-256 length"))
}
fn student_id(number: u64) -> String {
    format!("SYN{number:08}")
}
fn load_catalog(path: &Path) -> Result<(Catalog, String), String> {
    let raw = fs::read(path).map_err(|e| format!("reading {}: {e}", path.display()))?;
    let catalog: Catalog = serde_json::from_slice(&raw)
        .map_err(|e| format!("invalid catalog JSON: {e}"))?;
    if catalog.schema_version != "epa.atlas.v1" {
        return Err("invalid catalog schema".into());
    }
    if catalog.curriculum_type != "SYNTHETIC_DEMO" {
        return Err("only synthetic demonstrator catalogs supported".into());
    }
    if catalog.source.source_label.is_empty() || catalog.source.reference_url.is_empty() {
        return Err("source reference required".into());
    }
    if catalog.grades.is_empty() {
        return Err("grades required".into());
    }
    let mut levels = HashSet::new();
    const AREAS: [&str; 4] = ["MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS"];
    for grade in &catalog.grades {
        if !(6..=12).contains(&grade.grade_level) || !levels.insert(grade.grade_level) {
            return Err(format!("invalid or duplicate grade: {}", grade.grade_level));
        }
        if grade.subjects.is_empty() {
            return Err("subjects required".into());
        }
        let mut ids = HashSet::new();
        for subject in &grade.subjects {
            if subject.id.is_empty()
                || !ids.insert(subject.id.as_str())
                || !AREAS.contains(&subject.area.as_str())
            {
                return Err(format!("invalid or repeated subject: {}", subject.id));
            }
            if !subject.bncc_skill_codes.is_empty() {
                return Err("unverified BNCC skill links not permitted".into());
            }
        }
    }
    Ok((catalog, hex_sha256(&raw)))
}
fn inspect(path: &Path, students: u64, seed: u64) -> Result<Inspection, String> {
    if students == 0 {
        return Err("students must be >= 1".into());
    }
    let (catalog, digest) = load_catalog(path)?;
    let grades = catalog.grades.len() as u64;
    let subject_total = catalog.grades.iter().map(|g| g.subjects.len() as u64).sum::<u64>();
    // GENESIS v2/v3 defaults: 2 schools, 3 sections/grade, 4 terms/year.
    Ok(Inspection {
        schema_version: "epa.genesis.rs.inspect.v1",
        catalog_sha256: digest,
        generator_seed: seed,
        students,
        classes: grades * 2 * 3,
        enrollments: students * grades,
        subject_offerings: subject_total * 2 * 3,
        period_records: students * subject_total * 4,
        terms_per_year: 4,
        first_student_id: student_id(1),
        note: "Inspection only; no records generated or trained",
    })
}
fn usage() -> &'static str {
    "Usage:\n  genesis-rs seed <part> [part...]\n  genesis-rs inspect <catalog.json> <students> <seed>\n  genesis-rs generate-jsonl <catalog.json> <students> <seed> [start_year] [schools] [classes_per_grade]\n\nJSONL stdout is experimental; no native Parquet yet."
}
fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("seed") if args.len() >= 2 => {
            let parts: Vec<&str> = args[1..].iter().map(String::as_str).collect();
            println!("{}", stable_seed(&parts));
            Ok(())
        }
        Some("rng-probe") if args.len() == 2 => {
            let seed = args[1].parse::<u64>().map_err(|e| format!("rng seed: {e}"))?;
            let mut rng = rng::PythonRandom::seeded(seed);
            let result = serde_json::json!({
                "seed": seed,
                "first_random": rng.random(),
                "next_uniform_minus_1_to_1": rng.uniform(-1.0, 1.0),
                "next_gauss_standard": rng.gauss(0.0, 1.0),
                "next_randint_16_to_25": rng.randint(16, 25),
            });
            println!("{}", serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?);
            Ok(())
        }
        Some("generate-jsonl") if (4..=7).contains(&args.len()) => {
            let students = args[2].parse::<u64>().map_err(|e| format!("students: {e}"))?;
            let seed = args[3].parse::<u64>().map_err(|e| format!("seed: {e}"))?;
            let start_year = if args.len() >= 5 { args[4].parse::<u32>().map_err(|e| format!("start_year: {e}"))? } else { 2020 };
            let school_count = if args.len() >= 6 { args[5].parse::<u32>().map_err(|e| format!("schools: {e}"))? } else { 2 };
            let classes_per_grade = if args.len() >= 7 { args[6].parse::<u32>().map_err(|e| format!("classes_per_grade: {e}"))? } else { 3 };
            let (catalog, _) = load_catalog(Path::new(&args[1]))?;
            let stdout = std::io::stdout();
            let mut writer = std::io::BufWriter::new(stdout.lock());
            records::generate(&mut writer, &catalog, records::Config {
                students, seed, start_year, school_count, classes_per_grade
            })?;
            Ok(())
        }
        Some("inspect") if args.len() == 4 => {
            let students = args[2].parse::<u64>().map_err(|e| format!("students: {e}"))?;
            let seed = args[3].parse::<u64>().map_err(|e| format!("seed: {e}"))?;
            let result = inspect(Path::new(&args[1]), students, seed)?;
            println!("{}", serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?);
            Ok(())
        }
        _ => Err(usage().into()),
    }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(2);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn python_profile_seed_vector() {
        assert_eq!(stable_seed(&["20261029", "SYN00000001", "profile"]), 3051383292237719500);
    }
    #[test]
    fn python_section_seed_vector() {
        assert_eq!(stable_seed(&["20261029", "SYN00000001", "2020", "section"]), 17544070759066566074);
    }
    #[test]
    fn seed_changes_by_component() {
        assert_ne!(stable_seed(&["42", "alpha", "1"]), stable_seed(&["42", "alpha", "2"]));
        assert_eq!(stable_seed(&["42", "alpha", "1"]), 8312065688486285889);
    }
    #[test]
    fn student_identifier_is_stable() {
        assert_eq!(student_id(1), "SYN00000001");
        assert_eq!(student_id(120), "SYN00000120");
    }
}
