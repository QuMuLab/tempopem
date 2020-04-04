from regresser import build_regression_list
from sgpolicy import generate_sgpolicy, quality_func_action_count, quality_func_time_estimate, quality_func_min_idle
from temporal_policy import TempPolicy
from simulator import simulate_file
from linearizer import count_linearizations
from pop import *

from krrt.utils import get_opts
from krrt.planning.strips import progress_state

import os, time, random


def build_policy(filename):
    P = POP()
    P.load_custom_pop(filename)
    print "Linearizations: %d\n" % count_linearizations(P)
    #print P.init

    (suffixes, precset_mapping, apsp_mapping) = build_regression_list(P)

    import sys
    num_apsps = 0
    total_apsps = 0
    for s in apsp_mapping.keys():
        for a in apsp_mapping[s].keys():
            num_apsps += 1
            total_apsps += sum([len(d) for d in apsp_mapping[s][a].values()])
    print "\nNumber of actions: %d" % len(P.A_map)
    print "Number of candidates: %d" % num_apsps
    print "Total mappings: %d" % total_apsps
    print "Avg. mappings per context: %.2f\n" % (float(total_apsps) / float(num_apsps))

    #from old.policy import generate_policy
    #generate_policy(suffixes, precset_mapping)

    #for level in suffixes:
    #    for suff in level:
    #        print "\n\n  --{ Suffix }--"
    #        print "\n".join(map(str, suff.actions))
    #        print "\n  --{ Preconds }--"
    #        for ps in precset_mapping[suff]:
    #            print str(ps)

    #print "\n".join(map(str, apsp_mapping[suffixes[3].pop()].values()[0].keys()))

    pol = TempPolicy(generate_sgpolicy(suffixes, precset_mapping, quality_func_min_idle), apsp_mapping, P)

    #print pol.policy

    #print pol.get_action(0.0, P.G)
    #print pol.get_action(0.0, P.I)
    #print pol.get_action(0.0, P.I | P.G)

    #print P.network.nodes()

    return (pol, P)

def run_simulation(filename, pol, P):
    simulate_file(pol, filename, P.A_map, P.F_map)

def run_static(pol, P, mode, silent = False, alter_state = None, alter_settings = None):

    if not silent:
        print "\nRunning static simulation.\n"

    alter_state = alter_state or static_dynamics

    current_state = P.init.adds
    current_time = 0.0
    pol.reset()
    alter_settings = alter_settings or {}
    alter_settings['laundryok'] = True
    alter_settings['fullok'] = True
    going = True
    n_changes = 0
    count = 0

    while going:
        count += 1

        if count > 500:
            if not silent:
                print "!! Execution failed: loop of actions. !!"
            return (False, -1, -1, n_changes, -1)

        res = pol.get_action(current_time, current_state)

        if not res:
            if not silent:
                print "!! Execution failed: no action available. !!"
            return (False, -1, -1, n_changes, -1)
        else:
            (act, l, u) = res

        if 'startA_do_laundry' == act.operator:
            alter_settings['laundryok'] = False
        elif 'check_at_home' == act.operator:
            alter_settings['laundryok'] = True
        elif 'goto_sleep' == act.operator:
            alter_settings['laundryok']= False
            alter_settings['fullok']= False


        if not silent:
            print "Execute %s between %.2f and %.2f" % (str(act), l, u)

        if act == P.goal:
            going = False
        else:
            if not (act.precond <= current_state):
                if not silent:
                    print "!! Execution failed: action %s is not applicable. !!" % str(act)
                return (False, -1, -1, n_changes, -1)
            current_state = progress_state(current_state, act)
            n_changes += alter_state(current_state, P.F_map, silent, alter_settings)
            if 'lower' == mode:
                current_time += l
            elif 'upper' == mode:
                current_time += u
            elif 'mid' == mode:
                current_time += (l + u) / 2
            if not silent:
                print "Executing %s at %d:%02d (%f)\n\n-------------\n" % (str(act), int(current_time/60), int(current_time % 60), current_time)
            pol.add_action(current_time, act)
            current_time += TemporalConstraint.epsilon


    if ('stn' == pol.mode) and (not (P.goal.precond <= current_state)):
        if not silent:
            print "!! Execution failed: goal doesn't hold at the end of execution. !!"
        return (False, -1, -1, n_changes, -1)

    if not silent:
        print "\nGoal reached (%.2f)!" % (current_time + l)

    #for i in range(1, len(pol.trace)):
    #    op = pol.trace[i][0].operator
    #    t = pol.trace[i][1] - pol.trace[i-1][1]
    #    print "[self.pop.A_map['%s'], %f, %f]," % (op, t, t)

    return (True, current_time, count, n_changes, pol.replan_count)

def static_dynamics(s, fmap, silent, settings):
    return 0

def general_dynamics(s, fmap, silent, settings):

    full = fmap['f7']
    hungry = fmap['f6']
    laundry = fmap['f8']
    clean = fmap['f9']

    read = fmap['f11']
    movie = fmap['f12']
    groc = fmap ['f10']

    n_changes = 0

    # Handle the bad things

    if settings['fullok'] and (full in s) and (random.random() < settings['prob_hungry']):
        if not silent:
            print "-- Randomly becoming hungry."
        s.remove(full)
        s.add(hungry)
        n_changes += 1

    if settings['laundryok'] and (laundry in s) and (random.random() < settings['prob_unlaundry']):
        if not silent:
            print "-- Randomly dirtying the laundry."
        s.remove(laundry)
        n_changes += 1

    if (clean in s) and (random.random() < settings['prob_unclean']):
        if not silent:
            print "-- Randomly dirtying the kitchen."
        s.remove(clean)
        n_changes += 1

    # Handle the good things

    for (f, p) in [(laundry, settings['prob_laundry']),
                   (read, settings['prob_read']),
                   (movie, settings['prob_movie']),
                   (groc, settings['prob_groc']),
                   (full, settings['prob_full'])]:
        if random.random() < p:
            if not silent:
                print "-- Randomly add %s." % str(f)
            s.add(f)
            if (f == full) and (hungry in s):
                s.remove(hungry)
            n_changes += 1

    return n_changes


def pessimistic_dynamics(s, fmap, silent, settings):
    full = fmap['f7']
    hungry = fmap['f6']
    laundry = fmap['f8']

    n_changes = 0

    prob_hungry = settings.get('prob_hungry', 0.2)
    prob_laundry = settings.get('prob_unlaundry', 0.3)

    if settings['fullok'] and (full in s) and (random.random() < prob_hungry):
        if not silent:
            print "-- Randomly becoming hungry."
        s.remove(full)
        s.add(hungry)
        n_changes += 1

    if settings['laundryok'] and (laundry in s) and (random.random() < prob_laundry):
        if not silent:
            print "-- Randomly dirtying the laundry."
        s.remove(laundry)
        n_changes += 1

    return n_changes


if __name__ == '__main__':
    myargs, flags = get_opts()

    if '-plan' not in myargs:
        print "Error: Must choose a file for the STPOP (-plan)"
        os._exit(1)

    print
    (pol, P) = build_policy(myargs['-plan'])
    run_static(pol, P, 'mid')

    if '-file' in myargs:
        run_simulation(myargs['-file'], pol, P)

    print

