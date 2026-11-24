/* Native micro-benchmark of the two device-side variants of LO-ABE.
 *   device step : r = c0 - yT + sum_{j: t_j = 1} cs[j]   (m0 additions at most, no multiplications)
 *   local       : yT = ebar1.cA + sum_i e_i . c_i          (M + N*m multiply-accumulates) plus the device step
 * Word size W is 32 bits (prototype) or 64 bits (projected parameter set); arithmetic wraps modulo 2^W.
 * Build:  gcc -O2 -o device_microbench benchmarks/device_microbench.c
 * Run:    ./device_microbench <wordbits 32|64> <n> <k> <lambda> <N> <reps>
 * Output: one JSON line with median / Q1 / Q3 in nanoseconds for both variants.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

static double now_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e9 + t.tv_nsec; }
static int cmpd(const void *a, const void *b) { double x = *(const double *)a, y = *(const double *)b; return (x > y) - (x < y); }

#define KERNELS(T, SUF)                                                                            \
static T device_step_##SUF(T c0, T yT, const uint8_t *t, const T *cs, size_t m0) {                 \
    T acc = 0;                                                                                     \
    for (size_t j = 0; j < m0; j++) acc += cs[j] & (T)(-(T)t[j]);                                  \
    return c0 - yT + acc;                                                                          \
}                                                                                                  \
static T transform_##SUF(const int32_t *e1, const T *cA, size_t M, const int32_t *e2, const T *comps, size_t N, size_t m) { \
    T acc = 0;                                                                                     \
    for (size_t j = 0; j < M; j++) acc += (T)e1[j] * cA[j];                                        \
    for (size_t i = 0; i < N; i++) { const int32_t *e = e2 + i * m; const T *c = comps + i * m;    \
        for (size_t j = 0; j < m; j++) acc += (T)e[j] * c[j]; }                                    \
    return acc;                                                                                    \
}
KERNELS(uint32_t, 32)
KERNELS(uint64_t, 64)

static uint64_t rs = 88172645463325252ULL;
static uint64_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }

int main(int argc, char **argv) {
    if (argc < 7) { fprintf(stderr, "usage: %s wordbits n k lambda N reps\n", argv[0]); return 1; }
    int wb = atoi(argv[1]); size_t n = atol(argv[2]), k = atol(argv[3]), lam = atol(argv[4]), N = atol(argv[5]); int reps = atoi(argv[6]);
    size_t m = n * k, m0 = n * k + 2 * lam, M = m0 + m;
    uint8_t *t = malloc(m0); for (size_t j = 0; j < m0; j++) t[j] = rnd() & 1;
    int32_t *e1 = malloc(M * 4), *e2 = malloc(N * m * 4);
    for (size_t j = 0; j < M; j++) e1[j] = (int32_t)(rnd() % 4001) - 2000;
    for (size_t j = 0; j < N * m; j++) e2[j] = (int32_t)(rnd() % 4001) - 2000;
    void *cs = malloc(m0 * 8), *cA = malloc(M * 8), *comps = malloc(N * m * 8);
    for (size_t j = 0; j < m0; j++) ((uint64_t *)cs)[j] = rnd();
    for (size_t j = 0; j < M; j++) ((uint64_t *)cA)[j] = rnd();
    for (size_t j = 0; j < N * m; j++) ((uint64_t *)comps)[j] = rnd();
    if (wb == 32) { /* reinterpret as 32-bit words */ }
    double *d1 = malloc(reps * sizeof(double)), *d2 = malloc(reps * sizeof(double));
    volatile uint64_t sink = 0;
    for (int r = -3; r < reps; r++) {
        double a = now_ns();
        uint64_t x = wb == 32 ? device_step_32(7, 9, t, (const uint32_t *)cs, m0) : device_step_64(7, 9, t, (const uint64_t *)cs, m0);
        double b = now_ns();
        uint64_t y = wb == 32 ? transform_32(e1, (const uint32_t *)cA, M, e2, (const uint32_t *)comps, N, m) : transform_64(e1, (const uint64_t *)cA, M, e2, (const uint64_t *)comps, N, m);
        double c = now_ns();
        sink += x + y;
        if (r >= 0) { d1[r] = b - a; d2[r] = (c - b) + (b - a); }
    }
    qsort(d1, reps, sizeof(double), cmpd); qsort(d2, reps, sizeof(double), cmpd);
    printf("{\"wordbits\":%d,\"n\":%zu,\"k\":%zu,\"N\":%zu,\"m0\":%zu,\"M\":%zu,\"m\":%zu,\"reps\":%d,"
           "\"device_ns\":[%.0f,%.0f,%.0f],\"local_ns\":[%.0f,%.0f,%.0f]}\n", wb, n, k, N, m0, M, m, reps,
           d1[reps / 2], d1[reps / 4], d1[3 * reps / 4], d2[reps / 2], d2[reps / 4], d2[3 * reps / 4]);
    return (int)(sink == 42);
}
