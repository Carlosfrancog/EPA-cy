//! CPython-compatible random.Random for integer seeds on a 64-bit Python build.
//! Scope: MT19937, random(), uniform(), gauss(), randint() used by GENESIS v2/v3.
//! Never use for cryptography. Floating math may differ by a few ULP across runtimes.
use std::f64::consts::TAU;

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908_b0df;
const UPPER_MASK: u32 = 0x8000_0000;
const LOWER_MASK: u32 = 0x7fff_ffff;

#[derive(Clone)]
pub struct PythonRandom {
    mt: [u32; N],
    index: usize,
    gauss_next: Option<f64>,
}

impl PythonRandom {
    /// Reproduces CPython random.Random(seed) when seed is a nonnegative u64.
    /// CPython expands the integer into little-endian 32-bit words for init_by_array.
    pub fn seeded(seed: u64) -> Self {
        let keys = if seed > u32::MAX as u64 {
            vec![seed as u32, (seed >> 32) as u32]
        } else {
            vec![seed as u32]
        };
        let mut rng = Self { mt: [0; N], index: N, gauss_next: None };
        rng.init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        for _ in 0..N.max(keys.len()) {
            let prev = rng.mt[i - 1];
            rng.mt[i] = (rng.mt[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1664525)))
                .wrapping_add(keys[j]).wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                rng.mt[0] = rng.mt[N - 1];
                i = 1;
            }
            if j >= keys.len() { j = 0; }
        }
        for _ in 0..(N - 1) {
            let prev = rng.mt[i - 1];
            rng.mt[i] = (rng.mt[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                rng.mt[0] = rng.mt[N - 1];
                i = 1;
            }
        }
        rng.mt[0] = 0x8000_0000;
        rng
    }

    fn init_genrand(&mut self, seed: u32) {
        self.mt[0] = seed;
        for i in 1..N {
            let prev = self.mt[i - 1];
            self.mt[i] = 1812433253u32
                .wrapping_mul(prev ^ (prev >> 30))
                .wrapping_add(i as u32);
        }
        self.index = N;
    }

    fn next_u32(&mut self) -> u32 {
        if self.index >= N {
            for k in 0..N {
                let y = (self.mt[k] & UPPER_MASK) | (self.mt[(k + 1) % N] & LOWER_MASK);
                self.mt[k] = self.mt[(k + M) % N] ^ (y >> 1)
                    ^ if y & 1 != 0 { MATRIX_A } else { 0 };
            }
            self.index = 0;
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        y
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.next_u32() >> 5) as u64;
        let b = (self.next_u32() >> 6) as u64;
        ((a * 67108864 + b) as f64) / 9007199254740992.0
    }

    pub fn uniform(&mut self, low: f64, high: f64) -> f64 {
        low + (high - low) * self.random()
    }

    /// Equivalent to Python's getrandbits(k) for 1..=32 bits.
    fn getrandbits(&mut self, k: u32) -> u32 {
        assert!((1..=32).contains(&k));
        self.next_u32() >> (32 - k)
    }

    /// Inclusive bounds, using CPython's rejection sampling (_randbelow).
    pub fn randint(&mut self, low: u32, high: u32) -> u32 {
        assert!(low <= high);
        let width = (high as u64) - (low as u64) + 1;
        assert!(width <= u32::MAX as u64);
        let bits = 64 - width.leading_zeros();
        loop {
            let r = self.getrandbits(bits) as u64;
            if r < width {
                return low + r as u32;
            }
        }
    }

    /// CPython random.Random.gauss() uses a cached second Box-Muller value.
    pub fn gauss(&mut self, mu: f64, sigma: f64) -> f64 {
        let z = if let Some(cached) = self.gauss_next.take() {
            cached
        } else {
            let angle = self.random() * TAU;
            let radius = (-2.0 * (1.0 - self.random()).ln()).sqrt();
            self.gauss_next = Some(angle.sin() * radius);
            angle.cos() * radius
        };
        mu + z * sigma
    }
}

#[cfg(test)]
mod tests {
    use super::PythonRandom;

    fn close(actual: f64, expected: f64) {
        assert!((actual - expected).abs() < 1e-13, "{actual} != {expected}");
    }

    #[test]
    fn python_random_profile_golden_vector() {
        let mut rng = PythonRandom::seeded(3051383292237719500);
        for expected in [
            0.020478941183366572,
            0.21570014166473706,
            0.6832447225821833,
            0.9346351981797988,
            0.0984737818755157,
            0.8981031035274947,
        ] { close(rng.random(), expected); }
    }

    #[test]
    fn python_uniform_profile_golden_vector() {
        let mut rng = PythonRandom::seeded(3051383292237719500);
        for expected in [
            -1.5824194940948901,
            -0.9381895325063677,
            0.6047075845212047,
            1.434296153993336,
            -1.325036519810798,
        ] { close(rng.uniform(-1.65, 1.65), expected); }
    }

    #[test]
    fn python_gauss_golden_vector() {
        let mut rng = PythonRandom::seeded(16817751025044115065);
        for expected in [
            0.16693285048241108,
            -0.39862917304343004,
            -0.24721141319810494,
            0.8940651057263687,
        ] { close(rng.gauss(0.0, 0.95), expected); }
    }

    #[test]
    fn python_randint_golden_vector() {
        let mut rng = PythonRandom::seeded(16817751025044115065);
        for expected in [21, 17, 21, 20, 21] {
            assert_eq!(rng.randint(16, 25), expected);
        }
    }

    #[test]
    fn equal_seeds_are_deterministic() {
        let mut a = PythonRandom::seeded(42);
        let mut b = PythonRandom::seeded(42);
        for _ in 0..1000 {
            assert_eq!(a.random(), b.random());
        }
    }
}
