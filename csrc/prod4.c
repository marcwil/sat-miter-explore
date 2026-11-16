/* Meet-in-the-middle for 4-gate re-synthesis.
   P, Pinv: k x N permutation tables of single gates (int32), F: target permutation.
   Row r = i*k + j denotes the 2-gate circuit "g_i then g_j" with permutation
   Q_r[x] = P[j][P[i][x]].  We sort all rows by a 64-bit hash of Q_r, and for every
   row r compute the number of rows r' with Q_{r'} o Q_r = F (hash of
   F o Q_r^{-1}).  Sampling r with probability ~ qcount[r] and then r' uniformly
   among the matching rows gives a uniform sample of all 4-gate solutions.
   Returns the total number of solutions (sum of qcount). */
#include <stdint.h>
#include <stdlib.h>

typedef struct { uint64_t h; int32_t r; } HR;
static int cmp(const void *a, const void *b) {
    uint64_t x = ((const HR *)a)->h, y = ((const HR *)b)->h;
    return x < y ? -1 : x > y;
}

int64_t prod4(int N, int k, const int32_t *P, const int32_t *Pinv, const int32_t *F, const uint64_t *R,
              int32_t *rows_sorted, uint64_t *hash_sorted, int64_t *qstart, int32_t *qcount) {
    int64_t K = (int64_t)k * k;
    HR *a = malloc(sizeof(HR) * K);
    for (int i = 0; i < k; i++) {
        const int32_t *pi = P + (int64_t)i * N;
        for (int j = 0; j < k; j++) {
            const int32_t *pj = P + (int64_t)j * N;
            uint64_t h = 0;
            for (int x = 0; x < N; x++) h += R[x] * (uint64_t)pj[pi[x]];
            a[(int64_t)i * k + j].h = h; a[(int64_t)i * k + j].r = i * k + j;
        }
    }
    qsort(a, K, sizeof(HR), cmp);
    for (int64_t s = 0; s < K; s++) { rows_sorted[s] = a[s].r; hash_sorted[s] = a[s].h; }
    free(a);
    int64_t total = 0;
    for (int i = 0; i < k; i++) {
        const int32_t *ii = Pinv + (int64_t)i * N;
        for (int j = 0; j < k; j++) {
            const int32_t *jj = Pinv + (int64_t)j * N;
            /* q = F o (g_j o g_i)^{-1} = F o g_i^{-1} o g_j^{-1} : q[x] = F[ii[jj[x]]] */
            uint64_t h = 0;
            for (int x = 0; x < N; x++) h += R[x] * (uint64_t)F[ii[jj[x]]];
            /* binary search lower bound */
            int64_t lo = 0, hi = K;
            while (lo < hi) { int64_t mid = (lo + hi) / 2; if (hash_sorted[mid] < h) lo = mid + 1; else hi = mid; }
            int64_t st = lo; int32_t c = 0;
            while (lo < K && hash_sorted[lo] == h) { c++; lo++; }
            int64_t r = (int64_t)i * k + j;
            qstart[r] = st; qcount[r] = c; total += c;
        }
    }
    return total;
}
