/* prod4 with fingerprints: rows are sorted by a hash of the product evaluated on
   NS sample states only; every fingerprint match is verified on all N states, so
   qcount is exact. qstart/qlen give the candidate range (including false
   fingerprint matches) for sampling. */
#include <stdint.h>
#include <stdlib.h>

typedef struct { uint64_t h; int32_t r; } HR;
static int cmp(const void *a, const void *b) {
    uint64_t x = ((const HR *)a)->h, y = ((const HR *)b)->h;
    return x < y ? -1 : x > y;
}

int64_t prod4fp(int N, int k, const int32_t *P, const int32_t *Pinv, const int32_t *F, const uint64_t *R,
                int NS, const int32_t *xs, int32_t *rows_sorted, uint64_t *hash_sorted,
                int64_t *qstart, int32_t *qlen, int32_t *qcount) {
    int64_t K = (int64_t)k * k;
    HR *a = malloc(sizeof(HR) * K);
    for (int i = 0; i < k; i++) {
        const int32_t *pi = P + (int64_t)i * N;
        for (int j = 0; j < k; j++) {
            const int32_t *pj = P + (int64_t)j * N;
            uint64_t h = 0;
            for (int s = 0; s < NS; s++) h += R[s] * (uint64_t)pj[pi[xs[s]]];
            a[(int64_t)i * k + j].h = h; a[(int64_t)i * k + j].r = i * k + j;
        }
    }
    qsort(a, K, sizeof(HR), cmp);
    for (int64_t s = 0; s < K; s++) { rows_sorted[s] = a[s].r; hash_sorted[s] = a[s].h; }
    free(a);
    int32_t *q = malloc(sizeof(int32_t) * N);
    int64_t total = 0;
    for (int i = 0; i < k; i++) {
        const int32_t *ii = Pinv + (int64_t)i * N;
        for (int j = 0; j < k; j++) {
            const int32_t *jj = Pinv + (int64_t)j * N;
            uint64_t h = 0;
            for (int s = 0; s < NS; s++) h += R[s] * (uint64_t)F[ii[jj[xs[s]]]];
            int64_t lo = 0, hi = K;
            while (lo < hi) { int64_t mid = (lo + hi) / 2; if (hash_sorted[mid] < h) lo = mid + 1; else hi = mid; }
            int64_t st = lo, en = lo;
            while (en < K && hash_sorted[en] == h) en++;
            int32_t c = 0;
            if (en > st) {
                for (int x = 0; x < N; x++) q[x] = F[ii[jj[x]]];
                for (int64_t s = st; s < en; s++) {
                    int32_t r2 = rows_sorted[s];
                    const int32_t *p1 = P + (int64_t)(r2 / k) * N, *p2 = P + (int64_t)(r2 % k) * N;
                    int ok = 1;
                    for (int x = 0; x < N; x++) if (p2[p1[x]] != q[x]) { ok = 0; break; }
                    c += ok;
                }
            }
            int64_t r = (int64_t)i * k + j;
            qstart[r] = st; qlen[r] = (int32_t)(en - st); qcount[r] = c; total += c;
        }
    }
    free(q);
    return total;
}
