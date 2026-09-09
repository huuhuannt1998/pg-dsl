
# --- AUTHOR-ONLY GATE -------------------------------------------------------
# This script cross-checks the camera-ready manuscript against the raw result JSONs. The LaTeX
# source is not part of the public artifact, so on a fresh clone it exits
# cleanly instead of failing. The experiments themselves are reproducible
# without it: see README.md "Reproduce every paper number".
import os as _os, sys as _sys, pathlib as _p2
def _need(path, label):
    if not _os.path.exists(path):
        print(f"SKIP: {label} not present ({path}).")
        print("      This checker is author-only; it needs the LaTeX source, which the")
        print("      public artifact does not ship. Nothing is wrong with your clone.")
        _sys.exit(0)
# ---------------------------------------------------------------------------

import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import json
R=_ROOT+'/rebuttal_experiments/results/'
V=_ROOT+'/[FINAL](ACSAC 2026) PG-DSL/'
_need(V, 'camera-ready manuscript')
L=lambda f: json.load(open(R+f))
tex=open(V+'main.tex').read()
ev=open(V+'sections/06_evaluation.tex').read()
ds=open(V+'sections/04_system_design.tex').read()
ok=[];bad=[]
def chk(n,c): (ok if c else bad).append(n)

e1,e2,e4,e7,e11=L('e1_heldout_fpr.json'),L('e2_identity_binding.json'),L('e4_static_only.json'),L('e7_scale.json'),L('e11_mutation_coverage.json')
n1d,n1e,n1f,g=L('n1d_canonical8.json'),L('n1e_benign42.json'),L('n1f_z3_margin.json'),L('n1_gate_strong.json')
n2,n3,n3b,n4,n4b=L('n2_closed_world.json'),L('n3_command_log.json'),L('n3b_cmdlog_227.json'),L('n4_msb_union.json'),L('n4b_mcpshield_union.json')
n5,n5b,p3,p4,e8d=L('n5_coverage_curve.json'),L('n5b_coverage_curve.json'),L('p3_threshold_aware.json'),L('p4_second_substrate.json'),L('e8d_deltacov.json')

chk("E1 0/70 and 70/70", e1['rejected']==0 and e1['n_correct_entity']==70)
chk("E2 24/30, 30/30, 18/21, 21/21", e2['shipped_detected']==24 and e2['e2_detected']==30 and e2['separable_shipped']==18 and e2['separable_excitation']==21)
b=e11['by_class']
chk("E11 class row values", [b['M2_actuator_invert']['detected'],b['M3_magnitude_scale']['detected'],
    b['M4_sensor_swap_honest_label']['detected'],b['M5_sensor_swap_lying_label']['detected'],
    b['M1_actuator_swap']['detected'],b['M8_extra_side_effect']['detected'],
    b['M6_state_conditional']['detected'],b['M7_time_delayed']['detected']]==[8,4,30,24,4,0,0,0])
chk("E11 total 70/134", e11['aggregate_detected']==70 and e11['n_mutants']==134)
chk("hardened 94 / swap 8 / side 20", n2['total_cwa_plus_cmdlog']==94 and n3['actuator_swap_cmdlog']==8 and n2['by_class']['M8_extra_side_effect']['cwa']==20)
chk("cmdlog 0/42, 1/227 norm, 29/227 literal", n3b['results']['normalised']['canonical_14']==0
    and n3b['results']['normalised']['rejections']==1 and n3b['results']['literal']['rejections']==29)
chk("CW-A 0/42 and 0/227", n2['benign_fp_227']==0 and len(n2['benign_fp_42'])==0)
r5={x['K']:x for x in n5['rows']}
chk("N5 0/16 K3, 16/16 K30, benign 0", r5[3]['detected']==0 and r5[30]['detected']==16 and all(x['benign_fp']==0 for x in n5['rows']))
cur={c['w']:c for c in n5b['curve']}
chk("N5 widths 25%/100%/42%", round(cur[0.01]['K30'],2)==0.25 and cur[0.06]['K30']==1.0 and abs((1-cur[0.01]['K100'])-0.4167)<0.01)
chk("N1 18 twins / 144 / 756", n1d['n_twins']==18 and n1e['total_benign_verdicts']==756)
chk("N1 zero losses", len(n1d['detected_to_missed_flips'])==0 and n1e['induced_flips']==0)
chk("N1 gate 42 traj 35280 cmp 0 div", g['coverage']['trajectories']==42 and g['coverage']['scalar_comparisons']==35280 and g['divergences']==0)
chk("N1 only flip = W1 at drift0.02", n1d['flips']==[['drift0.02','W1']])
chk("N1 eps 12.8 / 8 of 18", max(t['eps_DT_emp'] for t in L('n1_perturbed_twin.json')['twins'])==12.8 and n1f['twins_below_threshold']==8)
chk("E4 A1-A3 yes, Z1 no, 1/14", e4['detection']['A1_type_confusion'] and not e4['detection']['Z1_transient_overshoot'] and e4['n_fp']==1)
chk("E7 14/15, 0.026ms", e7['prefilter']['lost']==14 and e7['prefilter']['ground_truth_unsafe']==15 and round(e7['per_replay_ms'],3)==0.026)
chk("P3 1.01 / rate 0.3", p3['empirical_sensor_boundary']==1.01 and 0.3 in p3['evading_rates'])
K=['qwen3:14b','mistral-nemo:12b','gemma2:9b','granite3.1-dense:8b','llama3.1:8b','phi4-mini:latest']
md={x['model']:x for x in e8d['models']}
chk("six-family FPR col", [md[k]['rejected'] for k in K]==[0,2,1,3,4,18])
chk("six-family R2 col", [md[k]['r2_violations'] for k in K]==[0,0,3,3,8,24])
chk("six-family delta_cov col", [md[k]['delta_cov_union'] for k in K]==[0,2,3,5,9,25])
u=n4['by_class']; mu=n4b['union']
chk("MSB PG-DSL union 24/1/0/1 of 33", [u[c]['union_detected'] for c in ('NC','PM','PI','OP')]==[24,1,0,1] and u['NC']['union_n']==33)
chk("MSB MCPShield union 3/0/0/0 of 33", [mu[c]['union_detected'] for c in ('NC','PM','PI','OP')]==[3,0,0,0] and mu['NC']['union_n']==33)
chk("MSB disjoint + non-NC tool", n4['n4_1_disjoint'] and all(h['target_tool']=='set_dosing_rate' for h in n4['non_nc_hits']))
chk("P4 1/8, 3/3, DPIT301", p4['benign_rejected']==1 and p4['attack_detected']==3 and p4['benign_rejections'][0]['tool']=='read_dp_DPIT301')
# manuscript-side assertions
chk("tex macro 28/31", '{\\tTwoCorrect}{28/31}' in tex)
chk("tex macro 90.3", '{\\tTwoCorrectPct}{90.3}' in tex)
chk("tex MSB macros 24/33", '24/33' in tex and '3/33' in tex)
chk("prefilter withdrawn", 'We withdraw that claim' in ds)
chk("35,280 in evaluation", '35{,}280' in ev)
chk("delta_cov range in evaluation", "\\deltaCovLo\\ to \\deltaCovHi" in ev and "{\\deltaCovLo}{$0/42$}" in tex and "{\\deltaCovHi}{$25/42$}" in tex)
chk("MSB n=33 in table", '& $33$ &' in ev)
chk("no stale SA 0/3", 'SA\\ 0/3' not in ev)
# ---------------------------------------------------------------------------
# Regression guards for the 2026-08-25 claim audit (30 confirmed defects).
# Token-boundary matching: a bare substring test let says("4 of 15") pass on
# "14 of 15" in the rebuttal verifier, hiding an unsupported number for two drafts.
# ---------------------------------------------------------------------------
import re as _re
_ap=open(V+'sections/99_appendix.tex').read()
_th=open(V+'sections/03_threat_model.tex').read()
_di=open(V+'sections/07_discussion.tex').read()
_cn=open(V+'sections/08_conclusion.tex').read()
def _tok(hay,s):
    for m in _re.finditer(_re.escape(s),hay):
        i,j=m.start(),m.end()
        b=hay[i-1] if i>0 else " "; a=hay[j] if j<len(hay) else " "
        if not (b.isalnum() or a.isalnum()): return True
    return False

# HIGH: plant invariant must gate inflow on MV101 AND a pump, outflow on MV201.
chk("plant invariant: wrong P101-outflow form absent (design)", "q_{\\text{out}}\\mathbf{1}_{\\text{P101 on}}" not in ds)
chk("plant invariant: conjunction + MV201 outflow present, wrong form absent (appendix)", "\\text{MV101 open} \\wedge" in _ap and "q_{\\text{out}}\\mathbf{1}_{\\text{MV201 open}}" in _ap and "q_{\\text{out}}\\mathbf{1}_{\\text{P101 on}}" not in _ap)
# HIGH: lifter mode is not uniformly qwen3 across campaigns.
chk("lifter mode scoped per campaign", "deterministic stub elsewhere" in ev and "lifter and matcher \\texttt{qwen3:14b} prompt" not in ev)
# HIGH: v0/v1 direction (v0 rejects 9/42 and lifts 13 dstate; v1 1/42 and 3).
chk("v0/v1 direction corrected", "dominates v0 on both axes" in _di and "v0 admits the elided" not in _di)
# MED: eps_AIT justification (band width 1.10 -> one tenth is 0.11, not 0.05).
chk("eps_AIT rationale corrected", "one-tenth of band" not in ds)
# MED/LOW: arithmetic and predicate fixes.
chk("Z3 margin 4.84 not 4.85", _tok(ds,"4.84\\times") and not _tok(ds,"4.85\\times")
    and round(5.0/1.032,2)==4.84)
chk("Z3 overflow predicate 99.5", _tok(_ap,r"L_{T101} \geq 99.5"))
chk("mutation per-class row correct", _tok(_ap,"$4/4$") and b['M3_magnitude_scale']['n']==4
    and b['M3_magnitude_scale']['detected']==4 and "Detection is\nperfect wherever" not in _ap)
chk("delta_cov soundness split 24 vs 25", _tok(_di,"$24/42$")
    and [m for m in e8d['models'] if m['model'].startswith('phi4')][0]['r2_violations']==24
    and [m for m in e8d['models'] if m['model'].startswith('phi4')][0]['delta_cov_union']==25)
chk("conclusion matches abstract precision", "five withheld at" in _cn)
chk("Z1/Z2 not called composition", "joint behaviour of individually-admitted" not in _th)
chk("W1 self-contradiction removed", "exceeding the matcher's cumulative budget" not in _th)
chk("no dead PROVENANCE path", "paper/PROVENANCE.md" not in _ap)
chk("227 corpus described honestly", "227$-paraphrase corpus (mistral-generated" not in ds)



# W1 mechanism: INVARLLM fires on a BAND invariant, never mass balance.
_t3=json.load(open(_ROOT+'/mission_3b/results/t3_partition_canonical.json'))
_inv=[v.get('invariant') for r in _t3['results'] for v in r.get('invarllm',{}).get('violations',[])]
chk("no mass-balance violation in canonical T3", all(str(i).startswith('band_') for i in _inv) and len(_inv)>0)
# E3 replaced the runtime column: the OLD partition file still says invarllm_only=[W1,W2],
# but the paper now reports the re-mined IDS (r3). Guard the paper against the r3 result.
_r3=json.load(open(R+'r3_invarllm_recalibrated.json')); _r1=json.load(open(R+'r1_k30_headline.json')); _r1b=json.load(open(R+'r1b_k30_qwen3.json')); _r2=json.load(open(R+'r2_invarllm_benign.json'))
chk("E3 re-mined IDS: 0/240 held-out benign FP", _r3['honest_fpr']['new_heldout_240']['fired']==0)
chk("E3 lanes: runtime-only empty, neither={W1,W2}, composed 6/8", _r3['lanes_new']['runtime_only']==[] and _r3['lanes_new']['missed_by_both']==['W1','W2'] and len(_r3['lanes_new']['composed'])==6)
chk("E2 old IDS fires on 42/42 honest traces", _r2['canonical_42']['fired']==42 and _r2['canonical_42']['mass_balance_violations']==0)
_i8=ev.find("$8/8$"); chk("paper reports 6/8 composed; the only 8/8 is the earlier-draft disclosure", _tok(ev,"$6/8$") and ev.count("$8/8$")==1 and "earlier draft reported" in ev[max(0,_i8-40):_i8] and "cover all $8$" not in ev and "covers all $8$" not in ev)
chk("Table 4: W1/W2 in neither lane, not composed-covered", ev.count("& neither      & No             & $100\\%$ & No")==2)
chk("T3 theorem restated one-directional", "A_{\\text{static}} = \\emptyset" in ev.replace("\n"," ") or "A_{\\text{static}} = \\emptyset" in ds.replace("\n"," "))
chk("E1 K=30: benign 0/420, shipped 86, hardened 110", _r1['benign']['rejected']==[] and _r1['shipped']['total']==86 and _r1['hardened']['total']==110)
chk("E1b K=30 qwen3: 6/8", _r1b['n_detected']==6 and not _r1b['results']['W1']['detected'] and not _r1b['results']['W2']['detected'])
chk("Table 9 carries the K=30 columns", _tok(_ap,"$86$") and _tok(_ap,"$110$") and "K{=}30" in _ap)
chk("prediction tally updated to 50/14", _tok(ev,"$50$") and "fourteen were falsified" in ev)
chk("W2 'grossly violated' claim removed everywhere", "grossly violated" not in ds and "mass-balance invariant on the runtime telemetry fires" not in _ap)
chk("W1 mass-balance claim removed (design)", "mass-balance invariant once the runtime" not in ds)
chk("W1 appendix reports the re-mined IDS miss", "misses $W_1$" in _ap and "r3\\_invarllm\\_recalibrated" in _ap)


# MSB split table: each union cell must be the row sum of its two constituents,
# and every printed cell must match the two union JSONs.
_n4=json.load(open(R+'n4_msb_union.json'))['by_class']
_n4b=json.load(open(R+'n4b_mcpshield_union.json'))['union']
_ok=True
for _c in ('NC','PM','PI','OP'):
    _p,_m=_n4[_c],_n4b[_c]
    _ok &= _p['hand_detected']+_p['grid_detected']==_p['union_detected']
    _ok &= _m['hand'][0]+_m['grid'][0]==_m['union_detected']
    for _s in (f"${_p['hand_detected']}/8$", f"${_p['grid_detected']}/25$",
               f"${_p['union_detected']}/33$", f"${_m['hand'][0]}/8$",
               f"${_m['grid'][0]}/25$", f"${_m['union_detected']}/33$"):
        _ok &= _s in _ap
chk("MSB split table matches n4/n4b and sums to the union", _ok)
chk("MSB split cross-referenced from the main table", "app:msbsplit" in ev and "app:msbsplit" in _ap)

print("PASS %d" % len(ok))
print("FAIL %d" % len(bad))
for x in bad: print("   XX", x)