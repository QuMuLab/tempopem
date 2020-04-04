
import math

from krrt.utils import get_opts, write_file
from krrt.stats.plots import plot

from run_example import *

POP_FILE = "testing/cog-pop"

def experiment1():
    print "Running experiment to compute the time savings"
    print "for precomputing the temporal network.\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    max_profile = {'prob_unlaundry':0.5,
                   'prob_hungry':0.4,
                   'prob_full':0.16,
                   'prob_laundry':0.16,
                   'prob_read':0.16,
                   'prob_movie':0.16,
                   'prob_groc':0.16}

    print "Running the simulation..."
    current_state = P.init.adds
    current_time = 0.0
    pol.reset()
    going = True
    max_profile['laundryok'] = True
    max_profile['fullok'] = True
    pre_times = []
    unpre_times = []

    while going:

        ((act, l, u), time_pre, time_unpre) = pol.get_action(current_time, current_state, 'timings')
        pre_times.append(time_pre)
        unpre_times.append(time_unpre)

        if 'startA_do_laundry' == act.operator:
            max_profile['laundryok'] = False
        elif 'check_at_home' == act.operator:
            max_profile['laundryok'] = True
        elif 'goto_sleep' == act.operator:
            max_profile['laundryok'] = False
            max_profile['fullok'] = False

        #print "Execute %s between %.2f and %.2f" % (str(act), l, u)

        if act == P.goal:
            going = False
        else:
            current_state = progress_state(current_state, act)
            general_dynamics(current_state, P.F_map, True, max_profile)
            current_time += (l + u) / 2
            print "Executing %s at %d:%02d (%f)\n\n-------------\n" % (str(act), int(current_time/60), int(current_time % 60), current_time)
            pol.add_action(current_time, act)
            current_time += TemporalConstraint.epsilon

    print "Processing the data..."
    x = []
    y = []
    for i in range(len(pre_times)):
        x.append(i+1)
        y.append(unpre_times[i] / pre_times[i])

    plot(x, y, x_label='Execution Trace', y_label='Ratio of Effort', col=False, xyline=False, y_log=True, x1line=True)



#############################################



def experiment2():
    print "Running experiment to see the number of causally and"
    print "temporally viable contexts that match at each step.\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    print "Running the simulation for early behaviour..."
    (lower_counts_causal, lower_counts_temporal, lower_counts_checked, lower_times) = exp_2_sim(pol, P, 'lower', pessimistic_dynamics)

    print "Running the simulation for late behaviour..."
    (upper_counts_causal, upper_counts_temporal, upper_counts_checked, upper_times) = exp_2_sim(pol, P, 'upper')

    print "Running the simulation for average behaviour..."
    (mid_counts_causal, mid_counts_temporal, mid_counts_checked, mid_times) = exp_2_sim(pol, P, 'mid')

    print

    print "Processing the lower behaviour data..."
    exp_2_proc(lower_counts_causal, lower_counts_temporal, lower_counts_checked, lower_times)

    print "Processing the upper behaviour data..."
    exp_2_proc(upper_counts_causal, upper_counts_temporal, upper_counts_checked, upper_times)

    print "Processing the average behaviour data..."
    exp_2_proc(mid_counts_causal, mid_counts_temporal, mid_counts_checked, mid_times)

def exp_2_sim(pol, P, mode, alter_state = None):

    alter_state = alter_state or static_dynamics

    current_state = P.init.adds
    current_time = 0.0
    pol.reset()
    going = True
    laundryok = True
    fullok = True
    counts_causal = []
    counts_temporal = []
    counts_checked = []
    times = []

    while going:
        #print pol.get_action(current_time, current_state, 'viable_counts')
        ((act, l, u), causal_count, temporal_count, checked_count) = pol.get_action(current_time, current_state, 'viable_counts')
        counts_causal.append(causal_count)
        counts_temporal.append(temporal_count)
        counts_checked.append(checked_count)

        if 'startA_do_laundry' == act.operator:
            laundryok = False
        elif 'check_at_home' == act.operator:
            laundryok = True
        elif 'goto_sleep' == act.operator:
            laundryok = False
            fullok = False

        #print "%d / %d / %d" % (causal_count, temporal_count, checked_count)

        #print "Execute %s between %.2f and %.2f" % (str(act), l, u)

        if act == P.goal:
            times.append(1440.0)
            going = False
        else:
            current_state = alter_state(progress_state(current_state, act), P.F_map, fullok=fullok, laundryok=laundryok)
            if 'lower' == mode:
                current_time += l
            elif 'upper' == mode:
                current_time += u
            elif 'mid' == mode:
                current_time += (l + u) / 2
            #print "Executing %s at %d:%02d (%f)\n\n-------------\n" % (str(act), int(current_time/60), int(current_time % 60), current_time)
            times.append(current_time)
            pol.add_action(current_time, act)
            current_time += TemporalConstraint.epsilon

    return (counts_causal, counts_temporal, counts_checked, times)

def exp_2_proc_xy_ploy(counts_causal, counts_temporal, counts_checked):
    xs = [counts_causal, counts_causal]
    ys = [counts_temporal, counts_checked]

    plot(xs, ys, x_label='\# of Causal Contexts', y_label='\# of Temporal and Computed Contexts', col=False, xyline=True, no_scatter=False, x_log=True, y_log=True)#,names=['Temporal Contexts', 'Checked Contexts'])

def exp_2_proc(counts_causal, counts_temporal, counts_checked, times):

    xs = [range(1,len(counts_causal)+1)] * 3
    #xs = [[(t / 60) for t in times]] * 3
    ys = [counts_causal, counts_temporal, counts_checked]

    print "\n".join(["%d,%d,%d" % (ys[0][i], ys[1][i], ys[2][i]) for i in range(len(ys[0]))])

    plot(xs, ys, x_label='Execution Trace', y_label='\# of Contexts', col=False, xyline=False, y_log=False, no_scatter=True, names=['Causally Viable', 'Temporally Viable', 'Checked'])



#############################################



def experiment3():
    print "Running experiment to try and profile the code usage during execution\n"
    print "Profile step:\n    python -m cProfile -o output.pstats evaluation.py exp3\n"
    print "Compilation:\n    python ~/Scripts/gprof2dot.py -f pstats output.pstats | dot -Tpng > profile.png\n\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    sim_num = 10000
    print "Running %d simulations..." % sim_num
    for i in range(sim_num):
        run_static(pol, P, mode = 'mid', silent = True)



#############################################



def experiment4():
    print "Running experiment to test the impact of having a long execution trace"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    print "Simulation a partial execution trace...\n"
    pol.add_action(360,P.A_map['wakeup'])
    pol.add_action(360.00001,P.A_map['serve_breakfast'])
    pol.add_action(360.00002,P.A_map['check_full'])
    pol.add_action(480,P.A_map['startA_drive_kids_school'])
    pol.add_action(510,P.A_map['endA_drive_kids_school'])
    pol.add_action(510.00001,P.A_map['startA_drive_mall'])
    pol.add_action(530.00001,P.A_map['endA_drive_mall'])
    pol.add_action(530.00002,P.A_map['check_at_mall'])
    pol.add_action(530.00003,P.A_map['startA_get_groceries'])
    pol.add_action(590.00003,P.A_map['endA_get_groceries'])
    pol.add_action(590.00004,P.A_map['startA_watch_movie'])
    pol.add_action(680.00004,P.A_map['endA_watch_movie'])
    pol.add_action(680.00005,P.A_map['startA_drive_home'])
    pol.add_action(700.00005,P.A_map['endA_drive_home'])
    pol.add_action(700.00006,P.A_map['startA_read_book'])

    print "Adding a number of start laundry actions (to pump up the force follow)..."
    s1 = set(map(P.F_map.get, ['f1', 'f4', 'f6', 'f7', 'f9', 'f10', 'f12', 'f14', 'noexec_do_laundry', 'exec_read_book',
                               'noexec_drive_school', 'noexec_drive_kids_school', 'noexec_drive_kids_home',
                               'noexec_drive_home', 'noexec_cook_meal', 'noexec_get_groceries', 'noexec_watch_movie',
                               'noexec_clean_kitchen', 'noexec_drive_mall']))

    s2 = set(map(P.F_map.get, ['f1', 'f4', 'f6', 'f7', 'f9', 'f10', 'f12', 'f14', 'exec_do_laundry', 'exec_read_book',
                               'noexec_drive_school', 'noexec_drive_kids_school', 'noexec_drive_kids_home',
                               'noexec_drive_home', 'noexec_cook_meal', 'noexec_get_groceries', 'noexec_watch_movie',
                               'noexec_clean_kitchen', 'noexec_drive_mall']))

    t = 701
    pre_times = []
    unpre_times = []

    for i in range(3):
        t += 20
        ((act, l, u), time_pre, time_unpre) = pol.get_action(t, s1, 'timings')
        pre_times.append(time_pre)
        unpre_times.append(time_unpre)
        print "%s, %f, %f" % (str(act), l, u)
        print "%f / %f" % (time_pre, time_unpre)
        print "Doing startA_read_book at %f\n\n#########################\n" % t
        pol.add_action(t,P.A_map['startA_read_book'])

    t += 15
    ((act, l, u), time_pre, time_unpre) = pol.get_action(t, s1, 'timings')
    pre_times.append(time_pre)
    unpre_times.append(time_unpre)
    print "%s, %f, %f" % (str(act), l, u)
    print "%f / %f" % (time_pre, time_unpre)
    print "Doing startA_do_laundry at %f\n\n#########################\n" % t
    pol.add_action(t,P.A_map['startA_do_laundry'])

    for i in range(6):
        ((act, l, u), time_pre, time_unpre) = pol.get_action(t, s2, 'timings')
        pre_times.append(time_pre)
        unpre_times.append(time_unpre)
        t += (l+u) / 2
        print "%s, %f, %f" % (str(act), l, u)
        print "%f / %f" % (time_pre, time_unpre)
        print "Doing startA_do_laundry at %f\n\n#########################\n" % t
        pol.add_action(t,P.A_map['startA_do_laundry'])

    print "Processing the data..."
    xs = [[], []]
    ys = [[], []]
    for i in range(len(pre_times)):
        xs[0].append(i+1)
        xs[1].append(i+1)
        ys[1].append(pre_times[i] / 100)
        ys[0].append(unpre_times[i] / 100)

    plot(xs, ys, x_label='Execution Trace', y_label='Time Required (s)', col=False, xyline=False, y_log=True, no_scatter=True, names=['Not Preprocessed', 'Preprocessed'])



#############################################


def experiment5():
    print "Running experiment to test success rate over a range of alteration probabilities\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    steps = 20
    prob_start = 0.0
    prob_end = 0.5
    prob_step = (prob_end - prob_start) / steps

    prob_laundry = prob_start

    x = []
    y = []

    sim_num = 100
    print "Running %d simulations for %d steps..." % (sim_num, steps)

    while prob_laundry < prob_end:
        worked = 0
        for i in range(sim_num):
            if run_static(pol, P, mode = 'mid', silent = True, alter_state=pessimistic_dynamics,
                          alter_settings={'prob_unlaundry':prob_laundry, 'prob_hungry':0.0})[0]:
                worked += 1

        x.append(prob_laundry)
        y.append(float(worked) / float(sim_num))
        print "\nProbability, Success Rate = %.2f,%.2f" % (x[-1], y[-1])

        prob_laundry += prob_step

    plot(x, y, x_label='Probability of Change', y_label='Success Rate', col=False, xyline=False)



#############################################



def experiment6():
    print "Running experiment to test various approaches in increasingly dynamic environments\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    prob_profiles = [
        {'prob_unlaundry':0.0,
         'prob_hungry':0.0,
         'prob_full':0.0,
         'prob_laundry':0.0,
         'prob_read':0.0,
         'prob_movie':0.0,
         'prob_groc':0.0},

        {'prob_unlaundry':0.05,
         'prob_hungry':0.1,
         'prob_full':0.04,
         'prob_laundry':0.04,
         'prob_read':0.04,
         'prob_movie':0.04,
         'prob_groc':0.04},

        {'prob_unlaundry':0.13,
         'prob_hungry':0.15,
         'prob_full':0.07,
         'prob_laundry':0.07,
         'prob_read':0.07,
         'prob_movie':0.07,
         'prob_groc':0.07},

        {'prob_unlaundry':0.21,
         'prob_hungry':0.2,
         'prob_full':0.1,
         'prob_laundry':0.1,
         'prob_read':0.1,
         'prob_movie':0.1,
         'prob_groc':0.1},

        {'prob_unlaundry':0.28,
         'prob_hungry':0.25,
         'prob_full':0.13,
         'prob_laundry':0.13,
         'prob_read':0.13,
         'prob_movie':0.13,
         'prob_groc':0.13},

        {'prob_unlaundry':0.35,
         'prob_hungry':0.3,
         'prob_full':0.16,
         'prob_laundry':0.16,
         'prob_read':0.16,
         'prob_movie':0.16,
         'prob_groc':0.16}
        ]


    # Means
    finish_times = {'us': [], 'seren': [], 'stn': []}
    action_counts = {'us': [], 'seren': [], 'stn': []}
    number_changes = {'us': [], 'seren': [], 'stn': []}

    # Computed
    success_rates = {'us': 0, 'seren': 0, 'stn': 0}

    sim_num = 1000
    first_run = True
    print "Running %d simulation profiles for %d iterations..." % (len(prob_profiles), sim_num)

    for settings in prob_profiles:

        if first_run:
            first_run = False
            sims = 1
        else:
            sims = sim_num

        for approach in ['us', 'seren', 'stn']:

            pol.mode = approach

            for i in range(sims):

                (success, f_time, a_count, n_changes, n_replans) = run_static(pol, P, mode = 'lower', silent = True,
                                                                   alter_state=general_dynamics, alter_settings=settings)

                finish_times[approach].append(f_time)
                if -1 == a_count:
                    a_count = 55
                action_counts[approach].append(a_count)
                number_changes[approach].append(n_changes)

                if success:
                    success_rates[approach] += 1


    #print finish_times
    #print action_counts
    #print number_changes

    print "\nSuccess rates: %s\n" % str(success_rates)

    print "Processing the data..."



    xs1 = [[], [], []]
    ys1 = [[], [], []]

    num_trials = len(finish_times['stn'])

    for i in range(num_trials):
        xs1[2].append(number_changes['stn'][i])
        ys1[2].append(action_counts['stn'][i])

        xs1[0].append(number_changes['us'][i])
        ys1[0].append(action_counts['us'][i])

        xs1[1].append(number_changes['seren'][i])
        ys1[1].append(action_counts['seren'][i])

    stn_success = []
    seren_success = []
    us_success = []

    stn_unsuccess = []
    seren_unsuccess = []
    us_unsuccess = []

    stn_change_counts = {}
    seren_change_counts = {}
    us_change_counts = {}

    for i in range(num_trials):
        if number_changes['stn'][i] not in stn_change_counts:
            stn_change_counts[number_changes['stn'][i]] = [0,0]
        if -1 == finish_times['stn'][i]:
            stn_unsuccess.append(number_changes['stn'][i])
            stn_change_counts[number_changes['stn'][i]][1] += 1
        else:
            stn_success.append(number_changes['stn'][i])
            stn_change_counts[number_changes['stn'][i]][0] += 1
            stn_change_counts[number_changes['stn'][i]][1] += 1

        if number_changes['us'][i] not in us_change_counts:
            us_change_counts[number_changes['us'][i]] = [0,0]
        if -1 == finish_times['us'][i]:
            us_unsuccess.append(number_changes['us'][i])
            us_change_counts[number_changes['us'][i]][1] += 1
        else:
            us_success.append(number_changes['us'][i])
            us_change_counts[number_changes['us'][i]][0] += 1
            us_change_counts[number_changes['us'][i]][1] += 1

        if number_changes['seren'][i] not in seren_change_counts:
            seren_change_counts[number_changes['seren'][i]] = [0,0]
        if -1 == finish_times['seren'][i]:
            seren_unsuccess.append(number_changes['seren'][i])
            seren_change_counts[number_changes['seren'][i]][1] += 1
        else:
            seren_success.append(number_changes['seren'][i])
            seren_change_counts[number_changes['seren'][i]][0] += 1
            seren_change_counts[number_changes['seren'][i]][1] += 1

    stn_success.sort()
    seren_success.sort()
    us_success.sort()

    xs2 = [[us_success[0]], [seren_success[0]], [stn_success[0]]]
    #ys2 = [[float(len(us_success)) / float(num_trials)], [float(len(seren_success)) / float(num_trials)], [float(len(stn_success)) / float(num_trials)]]
    #ys2 = [[1.0], [1.0], [1.0]]
    ys2 = [[float(len(us_success))], [float(len(seren_success))], [float(len(stn_success))]]

    for i in range(1,len(stn_success)):
        if stn_success[i] != xs2[2][-1]:
            xs2[2].append(stn_success[i])
            #ys2[2].append(float(len(stn_success) - i) / float(len(filter(lambda x: x >= stn_success[i], number_changes['stn']))))
            #ys2[2].append(float(len(filter(lambda x: (-1 != x) and (x <= stn_success[i]), stn_success))))
            ys2[2].append(float(len(stn_success) - i))

    for i in range(1,len(us_success)):
        if us_success[i] != xs2[0][-1]:
            xs2[0].append(us_success[i])
            #ys2[0].append(float(len(us_success) - i) / float(len(filter(lambda x: x >= us_success[i], number_changes['us']))))
            #ys2[0].append(float(len(filter(lambda x: (-1 != x) and (x <= us_success[i]), us_success))))
            ys2[0].append(float(len(us_success) - i))

    for i in range(1,len(seren_success)):
        if seren_success[i] != xs2[1][-1]:
            xs2[1].append(seren_success[i])
            #ys2[1].append(float(len(seren_success) - i) / float(len(filter(lambda x: x >= seren_success[i], number_changes['seren']))))
            #ys2[1].append(float(len(filter(lambda x: (-1 != x) and (x <= seren_success[i]), seren_success))))
            ys2[1].append(float(len(seren_success) - i))



    plot(xs1, ys1, x_label='Number of Changes', y_label='Actions in Plan', col=False, xyline=False, names=['Us', 'Opp', 'STN'])

    plot(xs2, ys2, x_label='Number of Changes', y_label='Successful Trials', no_scatter=True, col=False, xyline=False, names=['Our Approach', 'Opportunistic', 'STN Dispatch'])
    #plot(xs2, ys2, x_label='Number of Changes', y_label='Successful Trials', no_scatter=True, col=False, xyline=False, names=['Ours', 'Opp', 'STN'])

    xs3 = [[], [], []]
    ys3 = [[], [], []]

    xs4 = [[], [], []]
    ys4 = [[], [], []]

    for count in us_change_counts:
        if 5 < count < 30:
            xs3[0].append(count)
            xs4[0].append(count)
            ys3[0].append(us_change_counts[count][1])
            ys4[0].append(float(us_change_counts[count][0]) / float(us_change_counts[count][1]))

    for count in seren_change_counts:
        if 5 < count < 30:
            xs3[1].append(count)
            xs4[1].append(count)
            ys3[1].append(seren_change_counts[count][1])
            ys4[1].append(float(seren_change_counts[count][0]) / float(seren_change_counts[count][1]))

    for count in stn_change_counts:
        if 5 < count < 30:
            xs3[2].append(count)
            xs4[2].append(count)
            ys3[2].append(stn_change_counts[count][1])
            ys4[2].append(float(stn_change_counts[count][0]) / float(stn_change_counts[count][1]))

    plot(xs3, ys3, x_label='Number of Changes', y_label='Total Trials', no_scatter=False, col=False, xyline=False, names=['Our Approach', 'Opportunistic', 'STN Dispatch'])

    plot(xs4, ys4, x_label='Number of Changes', y_label='Success Rate', no_scatter=True, col=False, xyline=False, names=['Our Approach', 'Opportunistic', 'STN Dispatch'])



#############################################



def experiment7():
    print "Running experiment to test various approaches in increasingly dynamic environments\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    min_profile = {'prob_unlaundry':0.0,
                   'prob_hungry':0.0,
                   'prob_full':0.0,
                   'prob_laundry':0.0,
                   'prob_read':0.0,
                   'prob_movie':0.0,
                   'prob_groc':0.0}

    max_profile = {'prob_unlaundry':0.5,
                   'prob_hungry':0.4,
                   'prob_full':0.16,
                   'prob_laundry':0.16,
                   'prob_read':0.16,
                   'prob_movie':0.16,
                   'prob_groc':0.16}

    num_profiles = 20

    d_prob_unlaundry = (max_profile['prob_unlaundry'] - min_profile['prob_unlaundry']) / (num_profiles - 1)
    d_prob_hungry = (max_profile['prob_hungry'] - min_profile['prob_hungry']) / (num_profiles - 1)
    d_prob_full = (max_profile['prob_full'] - min_profile['prob_full']) / (num_profiles - 1)
    d_prob_laundry = (max_profile['prob_laundry'] - min_profile['prob_laundry']) / (num_profiles - 1)
    d_prob_read = (max_profile['prob_read'] - min_profile['prob_read']) / (num_profiles - 1)
    d_prob_movie = (max_profile['prob_movie'] - min_profile['prob_movie']) / (num_profiles - 1)
    d_prob_groc = (max_profile['prob_groc'] - min_profile['prob_groc']) / (num_profiles - 1)

    prob_profiles = [min_profile]

    for i in range(num_profiles - 2):
        prob_profiles.append(
            {
                'prob_unlaundry': prob_profiles[-1]['prob_unlaundry'] + d_prob_unlaundry,
                'prob_hungry': prob_profiles[-1]['prob_hungry'] + d_prob_hungry,
                'prob_full': prob_profiles[-1]['prob_full'] + d_prob_full,
                'prob_laundry': prob_profiles[-1]['prob_laundry'] + d_prob_laundry,
                'prob_read': prob_profiles[-1]['prob_read'] + d_prob_read,
                'prob_movie': prob_profiles[-1]['prob_movie'] + d_prob_movie,
                'prob_groc': prob_profiles[-1]['prob_groc'] + d_prob_groc
            }
        )

    prob_profiles.append(max_profile)

    # Means
    finish_times = {'us': [], 'seren': [], 'stn': []}
    action_counts = {'us': [], 'seren': [], 'stn': []}
    number_changes = {'us': [], 'seren': [], 'stn': []}

    # Computed
    success_rates = {'us': [], 'seren': [], 'stn': []}

    sim_num = 1000
    first_run = True
    print "Running %d simulation profiles for %d iterations..." % (len(prob_profiles), sim_num)

    for settings in prob_profiles:

        if first_run:
            first_run = False
            sims = 1
        else:
            sims = sim_num

        for approach in ['us', 'seren', 'stn']:

            pol.mode = approach

            successes = 0

            for i in range(sims):

                (success, f_time, a_count, n_changes, n_replans) = run_static(pol, P, mode = 'lower', silent = True,
                                                                   alter_state=general_dynamics, alter_settings=settings)

                finish_times[approach].append(f_time)
                if -1 == a_count:
                    a_count = 55
                action_counts[approach].append(a_count)
                number_changes[approach].append(n_changes)

                if success:
                    successes += 1

            success_rates[approach].append(float(successes) / float(sims))

    #print "\nSuccess rates: %s\n" % str(success_rates)

    print "Processing the data..."
    xs = [[], [], []]
    ys = [[], [], []]

    for i in range(num_profiles):
        xs[0].append(float(i) / float(num_profiles))
        ys[0].append(success_rates['us'][i])

        xs[1].append(float(i) / float(num_profiles))
        ys[1].append(success_rates['seren'][i])

        xs[2].append(float(i) / float(num_profiles))
        ys[2].append(success_rates['stn'][i])

    plot(xs, ys, x_label='Environment Variability', y_label='Success Rate', col=False, xyline=False, no_scatter=True, names=['Our Approach', 'Opportunistic', 'STN Dispatch'])

    # Write to the file just so we can use the data again
    write_file('exp7.out', map(str, xs) + map(str, ys))


#############################################



def experiment8():
    print "Running experiment to test the probability of replanning when things go wrong\n"

    print "Building the policy..."
    (pol, P) = build_policy(POP_FILE)

    min_profile = {'prob_unlaundry':0.0,
                   'prob_hungry':0.0,
                   'prob_unclean':0.0,
                   'prob_full':0.0,
                   'prob_laundry':0.0,
                   'prob_read':0.0,
                   'prob_movie':0.0,
                   'prob_groc':0.0}

    # 0.5 / 0.4
    max_profile = {'prob_unlaundry':0.5,
                   'prob_hungry':0.4,
                   'prob_unclean':0.5,
                   'prob_full':0.0,
                   'prob_laundry':0.0,
                   'prob_read':0.0,
                   'prob_movie':0.0,
                   'prob_groc':0.0}

    num_profiles = 20

    d_prob_unlaundry = (max_profile['prob_unlaundry'] - min_profile['prob_unlaundry']) / (num_profiles - 1)
    d_prob_hungry = (max_profile['prob_hungry'] - min_profile['prob_hungry']) / (num_profiles - 1)
    d_prob_unclean = (max_profile['prob_unclean'] - min_profile['prob_unclean']) / (num_profiles - 1)
    d_prob_full = (max_profile['prob_full'] - min_profile['prob_full']) / (num_profiles - 1)
    d_prob_laundry = (max_profile['prob_laundry'] - min_profile['prob_laundry']) / (num_profiles - 1)
    d_prob_read = (max_profile['prob_read'] - min_profile['prob_read']) / (num_profiles - 1)
    d_prob_movie = (max_profile['prob_movie'] - min_profile['prob_movie']) / (num_profiles - 1)
    d_prob_groc = (max_profile['prob_groc'] - min_profile['prob_groc']) / (num_profiles - 1)

    prob_profiles = [min_profile]

    for i in range(num_profiles - 2):
        prob_profiles.append(
            {
                'prob_unlaundry': prob_profiles[-1]['prob_unlaundry'] + d_prob_unlaundry,
                'prob_hungry': prob_profiles[-1]['prob_hungry'] + d_prob_hungry,
                'prob_unclean': prob_profiles[-1]['prob_unclean'] + d_prob_unclean,
                'prob_full': prob_profiles[-1]['prob_full'] + d_prob_full,
                'prob_laundry': prob_profiles[-1]['prob_laundry'] + d_prob_laundry,
                'prob_read': prob_profiles[-1]['prob_read'] + d_prob_read,
                'prob_movie': prob_profiles[-1]['prob_movie'] + d_prob_movie,
                'prob_groc': prob_profiles[-1]['prob_groc'] + d_prob_groc
            }
        )

    prob_profiles.append(max_profile)

    # Stats
    means = []
    stds = []
    max_replan = 0

    sim_num = 1000
    first_run = True
    print "Running %d simulation profiles for %d iterations..." % (len(prob_profiles), sim_num)

    for settings in prob_profiles:

        print "  Iteration #%d" % len(means)

        if first_run:
            first_run = False
            sims = 1
        else:
            sims = sim_num

        pol.mode = 'us'

        successes = 0
        replans = []

        for i in range(sims):

            (success, f_time, a_count, n_changes, n_replans) = run_static(pol, P, mode = 'lower', silent = True,
                                                               alter_state=general_dynamics, alter_settings=settings)

            if success:
                successes += 1
                replans.append(n_replans)

        if 0 != successes:
            means.append(float(sum(replans)) / float(successes))
            if 1 == sims:
                stds.append(0)
            else:
                stds.append(math.sqrt(sum([(x - means[-1]) ** 2 for x in replans]) / float(successes - 1)))
            max_replan = max(max_replan, max(replans))
        else:
            print "Error: Missing data point (0 successful runs)"
            replans.append(0)

    print "\nData:"
    for i in range(len(means)):
        print " %.2f (+/- %.3f)" % (means[i], stds[i])

    print "\nMax replans: %d" % max_replan

    print "\nProcessing the data..."
    x = [(float(i) / float(num_profiles)) for i in range(num_profiles)]
    #y = [float(i) / 20 for i in means]
    #yerr = [float(i) / 20 for i in stds]
    y = means
    yerr = stds

    print "\n--------------\n"

    print x
    print
    print y
    print
    print yerr

    plot(x, y, x_label='Environment Variability (X)', y_label='Mean Replans', col=False, xyline=False, no_scatter=True, y1line = True, yerr=yerr)

    # Write to the file just so we can use the data again
    write_file('exp8.out', map(str, x) + map(str, y) + map(str, yerr))



#############################################



if __name__ == '__main__':

    myargs, flags = get_opts()

    experiments = {
        'exp1':experiment1,
        'exp2':experiment2,
        'exp3':experiment3,
        'exp4':experiment4,
        'exp5':experiment5,
        'exp6':experiment6,
        'exp7':experiment7,
        'exp8':experiment8
        }

    for f in flags:
        if 'evaluation.py' != f:
            print
            experiments[f]()
            print
