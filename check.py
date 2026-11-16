"""Independent validation of instances (does not use model.py's simulator or rules).

  python check.py inst.json [--solver]
Checks
  1. transcript replay: each reordering only swaps gates that commute semantically
     (exhaustive on their wires) and each window replacement computes the same
     function (exhaustive on the window's wires); the replay ends in C_t.
  2. C_0 == C_t by brute force (n <= 16) or on 10^4 random inputs.
  3. optionally: CaDiCaL returns UNSAT on the miter CNF.
"""
import json, os, random, subprocess, sys, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
CADICAL = os.path.join(HERE, "tools/cadical/build/cadical")


def ev_gate(g, state):
    """state: dict/list wire -> bit. Returns new state (list copy)."""
    T, K, table = g
    idx = 0
    for j, w in enumerate(T):
        idx |= state[w] << j
    for j, w in enumerate(K):
        idx |= state[w] << (len(T) + j)
    out = table[idx]
    s = list(state)
    for j, w in enumerate(T):
        s[w] = (out >> j) & 1
    return s


def ev_seq(gates, state):
    for g in gates:
        state = ev_gate(g, state)
    return state


def local_equal(ga, gb, n):
    """Exhaustive check that gate sequences ga and gb agree on all assignments of
    the wires they touch (other wires are irrelevant)."""
    ws = sorted({w for g in ga + gb for w in list(g[0]) + list(g[1])})
    assert len(ws) <= 14, len(ws)
    for bits in range(1 << len(ws)):
        st = [0] * n
        for i, w in enumerate(ws):
            st[w] = (bits >> i) & 1
        if ev_seq(ga, st) != ev_seq(gb, st):
            return False
    return True


def check_gate_valid(g):
    T, K, table = g
    nT = len(T)
    assert len(set(T) | set(K)) == len(T) + len(K), "repeated wire"
    assert len(table) == 1 << (len(T) + len(K))
    for c in range(1 << len(K)):
        img = sorted(table[c << nT | x] for x in range(1 << nT))
        assert img == list(range(1 << nT)), "not a bijection for control %d" % c


def replay(js):
    n = js["params"]["n"]
    circ = [tuple(map(tuple, g[:2])) + (tuple(g[2]),) for g in js["C0"]]
    for g in circ:
        check_gate_valid(g)
    commute_cache = {}
    for step, r in enumerate(js["transcript"]):
        start, end, order, w = r["start"], r["end"], r["order"], r["w"]
        seg = circ[start:end]
        assert sorted(order) == list(range(len(seg))), "order not a permutation"
        # every inverted pair must commute
        posn = {k: i for i, k in enumerate(order)}
        for p in range(len(seg)):
            for q in range(p + 1, len(seg)):
                if posn[p] > posn[q]:
                    key = (seg[p], seg[q])
                    if key not in commute_cache:
                        commute_cache[key] = local_equal([seg[p], seg[q]], [seg[q], seg[p]], n)
                    assert commute_cache[key], "step %d: swapped non-commuting gates" % step
        new_seg = [seg[k] for k in order]
        old_win = new_seg[len(new_seg) - w:]
        new_win = [tuple(map(tuple, g[:2])) + (tuple(g[2]),) for g in r["new"]]
        for g in new_win:
            check_gate_valid(g)
        assert new_win != old_win, "step %d: replacement equals original" % step
        assert local_equal(old_win, new_win, n), "step %d: window not equivalent" % step
        circ = circ[:start] + new_seg[:len(new_seg) - w] + new_win + circ[end:]
    Ct = [tuple(map(tuple, g[:2])) + (tuple(g[2]),) for g in js["Ct"]]
    assert circ == Ct, "replay does not reproduce C_t"
    return len(js["transcript"])


def semantic(js, samples=10000):
    n = js["params"]["n"]
    C0 = [tuple(map(tuple, g[:2])) + (tuple(g[2]),) for g in js["C0"]]
    Ct = [tuple(map(tuple, g[:2])) + (tuple(g[2]),) for g in js["Ct"]]
    if n <= 16:
        inputs = range(1 << n)
    else:
        rnd = random.Random(12345)
        inputs = (rnd.getrandbits(n) for _ in range(samples))
    cnt = 0
    for x in inputs:
        st = [(x >> i) & 1 for i in range(n)]
        if ev_seq(C0, st) != ev_seq(Ct, st):
            return False, cnt
        cnt += 1
    return True, cnt


def solver_unsat(cnf_path, timeout=600):
    p = subprocess.run([CADICAL, "-q", cnf_path], capture_output=True, text=True, timeout=timeout)
    return p.returncode == 20


if __name__ == "__main__":
    path = sys.argv[1]
    js = json.load(open(path))
    k = replay(js)
    ok, cnt = semantic(js)
    msg = "%s: replay %d steps OK, semantic %s on %d inputs" % (os.path.basename(path), k, ok, cnt)
    if "--solver" in sys.argv:
        msg += ", cadical UNSAT=%s" % solver_unsat(path[:-5] + ".cnf")
    print(msg)
    sys.exit(0 if ok else 1)
