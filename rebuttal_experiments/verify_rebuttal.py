import json
R='/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments/results/'
REB='/Users/huanbui/Desktop/PG-DSL/(ACSAC 2026) PG-DSL_ Physics-Grounded Description Lifting for Admission-Time Defence of LLM-Controlled Industrial Cyber-Physical Systems/rebuttal/final-v5.md'
L=lambda f: json.load(open(R+f))
T=open(REB).read()
ok=[];bad=[]
def chk(n,c): (ok if c else bad).append(n)
import re as _re
def says(s):
    """True only if `s` occurs on a token boundary. A bare substring test let
    says("4 of 15") pass on the text "14 of 15" -- a vacuous check that hid an
    unsupported number for two drafts."""
    for _m in _re.finditer(_re.escape(s), T):
        _i,_j=_m.start(),_m.end()
        _b=T[_i-1] if _i>0 else " "; _a=T[_j] if _j<len(T) else " "
        if not (_b.isalnum() or _a.isalnum()): return True
    return False
def absent(s): return not says(s)

e1,e2,e4,e6,e7,e11=L('e1_heldout_fpr.json'),L('e2_identity_binding.json'),L('e4_static_only.json'),L('e6_adaptive.json'),L('e7_scale.json'),L('e11_mutation_coverage.json')
n1,n1c,n1d,n1e,n1f=L('n1_perturbed_twin.json'),L('n1c_margins.json'),L('n1d_canonical8.json'),L('n1e_benign42.json'),L('n1f_z3_margin.json')
g=L('n1_gate_strong.json'); n2,n3,n4=L('n2_closed_world.json'),L('n3_command_log.json'),L('n4_msb_union.json')
n5,n5b,p3,p4=L('n5_coverage_curve.json'),L('n5b_coverage_curve.json'),L('p3_threshold_aware.json'),L('p4_second_substrate.json')
e8c,e8d,n6b=L('e8c_crossmodel_fullpipe.json'),L('e8d_deltacov.json'),L('n6b_combined_benign227.json')
b=e11['by_class']

# --- preamble
chk("15 experiments claimed", says("Fifteen new experiments"))
chk("39 predictions / 11 falsified", says("of thirty-nine, eleven were falsified") and 17+22==39)
# --- A1
chk("A1 3 inseparable of 21", e2['n_pairs']-e2['separable_shipped']==3 and says("3 inseparable pairs of 21"))
chk("A1 25/31 -> 28/31", says("25/31 becomes 28/31"))
chk("A1 probe 30/30, shipped 24/30", e2['e2_detected']==30 and e2['shipped_detected']==24 and says("30/30") and says("24/30"))
chk("A1 zero FP", len(e2['false_positives_e2'])==0)
# --- A2
chk("A2 134 mutants 70/134", e11['n_mutants']==134 and e11['aggregate_detected']==70 and says("134 mutants") and says("70/134"))
chk("A2 24/30 falsified-label", b['M5_sensor_swap_lying_label']['detected']==24 and says("24/30 falsified-label"))
chk("A2 4/8 actuator-swap", b['M1_actuator_swap']['detected']==4 and says("4/8 actuator-swap"))
chk("A2 0/16,0/16,0/22", b['M6_state_conditional']['detected']==0 and b['M7_time_delayed']['detected']==0 and b['M8_extra_side_effect']['detected']==0 and says("0/16, 0/16, 0/22"))
chk("A2 only 1 of 14 dstate", e6['n_with_dstate']==1 and says("only 1 lifts a Delta-state clause"))
chk("A2 94/134", n2['total_cwa_plus_cmdlog']==94 and says("94/134"))
chk("A2 cmdlog 8/8", n3['actuator_swap_cmdlog']==8 and says("actuator-swap 8/8"))
chk("A2 unnamed-actuator 20/22", n2['by_class']['M8_extra_side_effect']['cwa']==20 and says("(20/22)"))
chk("A2 'no added benign cost' is TRUE", n6b['added_by_rules']==0 and says("no added benign cost"))
# --- B1
d=e4['detection']
chk("B1 A1-A3 det, Z1+Z3 missed, 1/14 FP",
    d['A1_type_confusion'] and d['A2_magnitude'] and d['A3_sensor_aliasing']
    and not d['Z1_transient_overshoot'] and not d['Z3_composition_a'] and not d['Z3_composition_b']
    and e4['n_fp']==1 and says("1/14 false positives") and says("misses Z1 and Z3"))
# --- B3
chk("B3 18 twins", n1d['n_twins']==18 and says("18 variants"))
chk("B3 144 attack verdicts", n1d['n_twins']*8==144 and says("144 attack"))
chk("B3 756 benign verdicts", n1e['total_benign_verdicts']==756 and says("756 benign"))
chk("B3 zero benign flips", n1e['induced_flips']==0 and says("zero benign flips"))
chk("B3 zero detected->missed", len(n1d['detected_to_missed_flips'])==0 and says("zero detected-to-missed"))
chk("B3 stub-mode 5/8 labelled", n1d['reproduces_published_stub_baseline'] and sum(1 for v in n1d['nominal'].values() if v)==5 and says("stub-mode 5/8 baseline"))
chk("B3 gate byte-identical", g['passed'] and g['divergences']==0)
chk("B3 A1 per-tool margin zero, composition catches",
    all(r['A1']['detected'] for r in n1d['rows'] if 'drift' in r['twin']) and says("composition alone then catches A1"))
chk("B3 eps_DT 12.8 max", max(t['eps_DT_emp'] for t in n1['twins'])==12.8 and says("12.8%-full"))
chk("B3 Z3 nominal 5.0, 8 of 18", n1f['measured_nominal']==5.0 and n1f['twins_below_threshold']==8 and says("8 of 18 twins"))
# --- B4
chk("B4 0.026 ms", round(e7['per_replay_ms'],3)==0.026 and says("0.026 ms"))
chk("B4 prefilter 14 of 15 (literal, measured)", e7['prefilter']['lost']==14 and e7['prefilter']['ground_truth_unsafe']==15 and says("14 of 15"))
_p1000=[r for r in e7['projection'] if r['catalog']==1000][0]
chk("B4 1000-tool projection = 25 s", round(_p1000['projected_seconds'])==25 and says("25 s") and says("1000-tool"))
chk("B4 unsupported 'charitably' figure removed", absent("charitably"))
# --- C1
r5={x['K']:x for x in n5['rows']}
cur={c['w']:c for c in n5b['curve']}
chk("C1 real-16: 0/16 at 3 published states", r5[3]['detected']==0 and r5[3]['n']==16 and says("0/16 at our 3 published states"))
chk("C1 real-16: 16/16 at 30 random states", r5[30]['detected']==16 and says("16/16 at 30 random states"))
chk("C1 point triggers 42% invisible @K=100", abs((1-cur[0.01]['K100'])-0.4167)<0.01 and says("42% invisible at K=100"))
chk("C1 benign 0/14 all K", all(x['benign_fp']==0 for x in n5['rows']) and all(v==0 for v in n5b['benign_by_K'].values()) and says("0/14 at every K"))
# --- C2
u=n4['by_class']
chk("C2 union 24/1/0/1 of 33", [u[c]['union_detected'] for c in ('NC','PM','PI','OP')]==[24,1,0,1] and u['NC']['union_n']==33 and says("24/33"))
chk("C2 disjoint", n4['n4_1_disjoint'] and says("disjoint"))
chk("C2 both non-NC = set_dosing_rate", all(h['target_tool']=='set_dosing_rate' for h in n4['non_nc_hits']) and says("set_dosing_rate"))
# --- C3
chk("C3 1.01 @ eps 1.0, rate 0.3", p3['empirical_sensor_boundary']==1.01 and p3['eps_DT']==1.0 and 0.3 in p3['evading_rates'] and says("caught at 1.01") and says("rate 0.3"))
# --- C4
chk("C4 0/70, entity 70/70", e1['rejected']==0 and e1['n_correct_entity']==70 and says("0/70") and says("entity 70/70"))
# --- C5
K=['qwen3:14b','gemma2:9b','mistral-nemo:12b','granite3.1-dense:8b','llama3.1:8b','phi4-mini:latest']
m={x['model']:x for x in e8c['models']}; md={x['model']:x for x in e8d['models']}
chk("C5 FPR col 0,1,2,3,4,18", [m[k]['rejected'] for k in K]==[0,1,2,3,4,18])
chk("C5 R2 col 0,3,0,3,8,24", [m[k]['inferred_dstate_lifts'] for k in K]==[0,3,0,3,8,24])
chk("C5 wrong-lift column = per-family delta_cov", all(says(f"{md[k]['delta_cov_union']}/42") for k in K) and says("counted once"))
chk("C5 llama reproduces Table 7", m['llama3.1:8b']['rejected']==4 and says("reproduces Table 7 exactly"))
# --- C6
chk("C6 1/8 benign, 3/3 attacks", p4['benign_rejected']==1 and p4['attack_detected']==3 and says("benign rejection 1/8") and says("poisoned tools 3/3"))
chk("C6 7/8 lift, DPIT301 closed", p4['benign_rejections'][0]['tool']=='read_dp_DPIT301' and says("7/8 lift") and says("DPIT301 fails closed"))
# --- no stale claims
for s in ("0/42 and 1/227","eight were falsified","A1 is admitted","r=0.978","at 0/227 benign cost"):
    chk(f"no stale: {s!r}", s not in T)
print(f"PASS {len(ok)}\nFAIL {len(bad)}")
for x in bad: print("   XX",x)
