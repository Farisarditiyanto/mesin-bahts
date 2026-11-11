// SPDX-License-Identifier: AGPL-3.0-or-later
//! Experimental implementation; rules are supplied by mesin/norma.py.
use std::collections::HashMap;
use std::borrow::Cow;
use fancy_regex::Regex as Fancy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use regex::Regex;

#[pyclass]
struct Normalizer {
    tags: Regex,
    harakat: Regex,
    hormat: Regex,
    ligatur: Regex,
    presentasi: Regex,
    bukan_huruf: Regex,
    bukan_abjad: Regex,
    syai: Fancy,
    tanpa_hamzah: Fancy,
    ibnu: Fancy,
    sama: Vec<Option<char>>,
    ejaan: Vec<(String, String)>,
    nfkc: Py<PyAny>,
}

fn invalid(e: impl std::fmt::Display) -> PyErr { PyValueError::new_err(e.to_string()) }

#[pymethods]
impl Normalizer {
    #[new]
    fn new(patterns: HashMap<String, String>, sama: Vec<(char, char)>, ejaan: Vec<(String, String)>, nfkc: Py<PyAny>) -> PyResult<Self> {
        let get = |name: &str| patterns.get(name).ok_or_else(|| invalid(format!("missing rule: {name}")));
        let re = |name: &str| Regex::new(get(name)?).map_err(invalid);
        let fancy = |name: &str| Fancy::new(get(name)?).map_err(invalid);
        let mut letters = vec![None; sama.iter().map(|(c, _)| *c as usize + 1).max().unwrap_or(0)];
        for (from, to) in sama { letters[from as usize] = Some(to); }
        Ok(Self {
            tags: re("TAGS")?, harakat: re("HARAKAT")?, hormat: re("HORMAT")?,
            ligatur: re("LIGATUR_HORMAT")?, presentasi: re("PRESENTASI")?,
            bukan_huruf: re("BUKAN_HURUF")?, bukan_abjad: re("BUKAN_ABJAD")?,
            syai: fancy("SYAI")?, tanpa_hamzah: fancy("SYAI_TANPA_HAMZAH")?, ibnu: fancy("IBNU")?,
            sama: letters, ejaan, nfkc,
        })
    }

    fn norm(&self, py: Python<'_>, text: &str) -> PyResult<String> { self.convert(py, text, false) }
    fn padat(&self, py: Python<'_>, text: &str) -> PyResult<String> { self.convert(py, text, true) }
}

impl Normalizer {
    fn convert(&self, py: Python<'_>, text: &str, compact: bool) -> PyResult<String> {
        let mut s = text.replace(['ﷺ', 'ﷻ'], " ");
        if let Cow::Owned(v) = self.ligatur.replace_all(&s, " ") { s = v; }
        if s.contains('﷽') { s = s.replace('﷽', " بسم الله الرحمن الرحيم "); }
        // Match the host Python's Unicode database, including older supported Pythons.
        if self.presentasi.is_match(&s) { s = self.nfkc.call1(py, ("NFKC", &s))?.extract(py)?; }
        if let Cow::Owned(v) = self.tags.replace_all(&s, "") { s = v; }
        if let Cow::Owned(v) = self.harakat.replace_all(&s, "") { s = v; }
        if let Cow::Owned(v) = self.hormat.replace_all(&s, " ") { s = v; }
        if s.contains("شئ") { s = self.syai.try_replacen(&s, 0, "شيء").map_err(invalid)?.into_owned(); }
        if s.contains("شي") { s = self.tanpa_hamzah.try_replacen(&s, 0, "${1}شيء").map_err(invalid)?.into_owned(); }
        s = s.chars().map(|c| self.sama.get(c as usize).copied().flatten().unwrap_or(c)).collect();
        for (from, to) in &self.ejaan { if s.contains(from) { s = s.replace(from, to); } }
        if s.contains("ابن") { s = self.ibnu.try_replacen(&s, 0, "بن").map_err(invalid)?.into_owned(); }
        if compact { Ok(self.bukan_abjad.replace_all(&s, "").into_owned()) }
        else { Ok(self.bukan_huruf.replace_all(&s, " ").trim().to_owned()) }
    }
}

#[pymodule]
fn _bahts_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Normalizer>()?;
    Ok(())
}
