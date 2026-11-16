/* Candidate filter for 3-gate XOR re-synthesis: for all (i1, i3) compute
   H = g3^-1 o F o g1^-1 and keep pairs for which H flips at most one fixed bit
   (i.e. H could be a single-target XOR gate). Exact gate lookup is done in Python. */
#include <stdint.h>
int search3(int N, int k, const int64_t *Pinv, const int64_t *F, int64_t *out, int maxout) {
    int cnt = 0;
    for (int i1 = 0; i1 < k; i1++) {
        const int64_t *g1i = Pinv + (int64_t)i1 * N;
        for (int i3 = 0; i3 < k; i3++) {
            const int64_t *g3i = Pinv + (int64_t)i3 * N;
            int64_t abit = 0; int ok = 1;
            for (int x = 0; x < N; x++) {
                int64_t d = g3i[F[g1i[x]]] ^ x;
                if (!d) continue;
                if (d & (d - 1)) { ok = 0; break; }
                if (!abit) abit = d; else if (d != abit) { ok = 0; break; }
            }
            if (ok && abit) {
                if (cnt < maxout) { out[2 * cnt] = i1; out[2 * cnt + 1] = i3; }
                cnt++;
            }
        }
    }
    return cnt;
}
