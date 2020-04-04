
from lifter import lift_POP, make_layered_POP
from regresser import build_regression_list
from policy import generate_policy, generate_dump, generate_dot, generate_graph, generate_stats, compute_coverage
from sgpolicy import generate_sgpolicy
from simulator import Simulation, POPPolicy, AllStateSerialPolicy, CurrentStateSerialPolicy
from linearizer import count_linearizations, linearize

from krrt.planning.strips.representation import parse_problem, generate_action, Action
from krrt.planning import parse_output_FF
from krrt.stats import randomized_pairwise_t_test as t_test

from krrt.utils import get_opts, write_file, save_CSV, read_file
import os, time, random

USAGE_STRING = """
Usage: python lifter.py <TASK> -<option> <argument> -<option> <argument> ...

        Where <TASK> may be:
          policy: Generate the policy from input domain and problem file.
          simulation: Run the simulation with the given parameters.
          analytic: Compute the analytic comparison of state coverage.
          policyimpact: Measure the impact using a policy has (over using just regression checking)

        The options for the 'policy' task are:
          -domain <pddl domain file>
          -prob <pddl problem file>
          -out <name of directory for output>
          -popf <yes/no>: Use popf for creating a solution
          -bound <# of linearization bound> (optional)

        The options for the 'simulation' task are:

             [ Mandatory ]
          -domain <pddl domain file>
          -prob <pddl problem file>
          -ffout <name of FF output file>
          -policy <name of the POP policy file>

             [ Optional ]
          -out <directory to where the files are located>
          -trials <number of trials to perform> (default: 1)
          -dynamics <angelic/demonic/neutral> (default: neutral)
          -seed <float number for the random seed>
          -perturber <perturber technique: none/prob/probhelpful/probharmful/fritz/fritzharmful> (default: none)
          -relevant <yes/no> Use only relevant fluents. (default: no)
          -simname <file name for the simulation results>
          -dumppunt <directory to dump the punted init states of the POP Policy>

             [ -perturber prob Specific ]
          -perprob <probability that a fluent is changed>
          -permax <maximum number of fluents to change>

        The options for the 'analytic' task are:
          -domain <pddl domain file>
          -prob <pddl problem file>
          -ffout <name of FF output file>
          -policy <name of the POP policy file>

        The options for the 'policyimpact' task are:
          -domain <pddl domain file>
          -prob <pddl problem file>
          -ffout <name of FF output file>
        """

def do_policy_impact(settings):
    # Create the POP policy for a single linearization
    serial_pop = lift_POP(settings['-domain'], settings['-prob'], settings['-ffout'], True)
    rl, mapping = build_regression_list(serial_pop)
    policy = generate_policy(rl, mapping)
    assert count_linearizations(serial_pop) == 1
    poppolicy = POPPolicy(generate_dump(policy).split("\n"))


    # Create the Fritz policy
    plan = parse_output_FF(settings['-ffout'])
    allF, allA, I, G = parse_problem(settings['-domain'], settings['-prob'])
    fritzpolicy = AllStateSerialPolicy(plan, allF, allA, I, G)

    # Set up the simulation
    lookup = {'False': False}
    F = I.copy()
    A = set()

    # Normal actions
    for act in plan.actions:
        a = generate_action(allA[act.operator], act)
        F |= a.adds | a.precond | a.dels
        A.add(a)

    # Goal action
    goal = Action(G, set(), set(), "goal")
    F |= goal.precond
    A.add(goal)

    for action in A:
        lookup[str(action)] = action

    for fluent in F:
        lookup[str(fluent)] = fluent

    # Run the simulation
    states = []
    for i in range(10000):
        states.append(set())
        for f in F:
            if random.choice([True, False]):
                states[-1].add(f)

    pop_count = 0
    fritz_count = 0

    time_pop_start = time.time()
    for state in states:
        if 'False' == str(poppolicy.get_action(lambda x: x in state, lookup)):
            pop_count += 1
    time_pop_end = time.time()

    time_fritz_start = time.time()
    for state in states:
        if 'False' == str(fritzpolicy.get_action(lambda x: x in state, lookup)):
            fritz_count += 1
    time_fritz_end = time.time()

    assert pop_count == fritz_count

    print "\nPunt Count: %d" % pop_count
    print "Punt Ratio: %3.4f" % (float(pop_count) / 10000.0)
    print "Fritz approach took %3.4f times longer.\n" % (float(time_fritz_end - time_fritz_start) / float(time_pop_end - time_pop_start))
    print "Avg serial time: %f\n" % (float(time_fritz_end - time_fritz_start) / 10000.0)
    print "Avg policy time: %f\n" % (float(time_pop_end - time_pop_start) / 10000.0)


def do_analytic(settings):
    # Count the policy coverage
    policy_text = read_file(settings['-policy'])

    num_fluents = int(policy_text.pop(0))
    root = policy_text.pop(0)

    nodes = {}
    edges = {}

    num_nodes = int(policy_text.pop(0))
    for n in range(num_nodes):
        num, val = policy_text.pop(0).split('/')
        nodes[num] = val
        edges[num] = {}

    num_edges = int(policy_text.pop(0))
    for e in range(num_edges):
        u,v,hl = policy_text.pop(0).split('/')
        edges[u][hl == 'h'] = v

    scores = {}
    anti_scores = {}
    for n in nodes:
        scores[n] = False
        anti_scores[n] = False

    def coverage(node, max_depth, depth):
        if not scores[node]:
            if len(edges[edges[node][True]]) > 0:
                high_score = coverage(edges[node][True], max_depth, depth+1)
                high_anti_score = anti_scores[edges[node][True]]
            else:
                if nodes[edges[node][True]] != 'False':
                    high_score = 2 ** (max_depth - depth - 1)
                    high_anti_score = 0
                else:
                    high_score = 0
                    high_anti_score = 2 ** (max_depth - depth - 1)

            if len(edges[edges[node][False]]) > 0:
                low_score = coverage(edges[node][False], max_depth, depth+1)
                low_anti_score = anti_scores[edges[node][False]]
            else:
                if nodes[edges[node][False]] != 'False':
                    low_score = 2 ** (max_depth - depth - 1)
                    low_anti_score = 0
                else:
                    low_score = 0
                    low_anti_score = 2 ** (max_depth - depth - 1)

            scores[node] = high_score + low_score
            anti_scores[node] = high_anti_score + low_anti_score

        return scores[node]

    policy_coverage = coverage(root, num_fluents, 0)
    assert policy_coverage + anti_scores[root] == 2**num_fluents


    # Count the Fritz coverage
    serial_pop = lift_POP(settings['-domain'], settings['-prob'], settings['-ffout'], True)
    rl, mapping = build_regression_list(serial_pop)
    policy = generate_policy(rl, mapping)
    assert count_linearizations(serial_pop) == 1
    fritz_coverage = compute_coverage(policy, num_fluents, 0)

    print "\n\nPOP Policy:\t %d" % policy_coverage
    print "Fritz Policy:\t %d" % fritz_coverage
    print "Ratio: %3.5f\n" % (float(policy_coverage) / float(fritz_coverage))

def do_simulation(settings):

    if '-seed' in settings:
        seed = float(settings['-seed'])
    else:
        seed = time.time()

    print "\nUsing random seed %f\n" % float(seed)
    random.seed(seed)


    if '-dumppunt' in settings:
        if not os.path.exists(settings['-dumppunt']):
            os.system("mkdir %s" % settings['-dumppunt'])


    if '-out' not in settings:
        settings['-out'] = '.'

    if '-dynamics' not in settings:
        settings['-dynamics'] = 'neutral'

    if '-simname' not in settings:
        settings['-simname'] = 'simulation_results.csv'

    if '-relevant' not in settings:
        settings['-relevant'] = 'no'

    settings['-domain'] = os.path.join(settings['-out'], settings['-domain'])
    settings['-prob'] = os.path.join(settings['-out'], settings['-prob'])
    settings['-ffout'] = os.path.join(settings['-out'], settings['-ffout'])
    settings['-policy'] = os.path.join(settings['-out'], settings['-policy'])

    plan = parse_output_FF(settings['-ffout'])
    allF, allA, I, G = parse_problem(settings['-domain'], settings['-prob'])

    F = I.copy()
    A = set()

    # Normal actions
    for act in plan.actions:
        a = generate_action(allA[act.operator], act)
        F |= a.adds | a.precond | a.dels
        A.add(a)

    # Goal action
    goal = Action(G, set(), set(), "goal")
    F |= goal.precond
    A.add(goal)

    settings['F'] = F
    settings['A'] = A
    settings['I'] = I
    settings['G'] = G

    if '-trials' not in settings:
        settings['-trials'] = 1

    SCORES = {}
    COUNTS = {}
    POP_COULDA = 0
    POP_FAILED = 0

    sim = Simulation(settings)

    sim.add_policy(POPPolicy(read_file(settings['-policy'])))
    sim.add_policy(CurrentStateSerialPolicy(plan, allF, allA, I, G))
    sim.add_policy(AllStateSerialPolicy(plan, allF, allA, I, G))

    total_trials = int(settings['-trials'])
    last = 0.0

    for trial in range(total_trials):

        progress = float(trial) / float(total_trials)
        if progress >= last:
            print "%3.1f%% Complete" % (progress * 100)
            last += 0.1

        sim.reset()

        while sim.going:
            sim.do_step()
            sim.perturb()

        for policy in sim.scores:

            if policy not in SCORES:
                SCORES[policy] = []
                COUNTS[policy] = 0

            SCORES[policy].append(sim.scores[policy])
            if sim.reached_goal[policy]:
                COUNTS[policy] += 1
            elif policy == "POP Policy":
                POP_FAILED += 1

        if sim.POP_could_have_reached_goal:
            POP_COULDA += 1

    if int(settings['-trials']) != 1:

        data = [['Policy', 'Ratio of Successful Plans', 'Mean Distance', 'Standard Deviation', 'Distance 1', '...']]

        print "\n\n  -{ Scores }-\n"

        for policy in SCORES:
            ratio = float(COUNTS[policy]) / float(total_trials)
            mean = float(sum(SCORES[policy])) / float(settings['-trials'])
            std = (float(sum([(item - mean)**2 for item in SCORES[policy]])) / float(settings['-trials']))**0.5
            print "%s: %3.3f +/- %3.3f (%d / %d = %3.2f%%)" % (policy, mean, std, COUNTS[policy], total_trials, float(COUNTS[policy]*100) / float(total_trials))
            data.append([policy, ratio, mean, std] + SCORES[policy])

        save_CSV(data, os.path.join(settings['-out'], settings['-simname']))

        #for policy1 in SCORES:
            #for policy2 in SCORES:
                #if policy1 == 'POP Policy':
                    #if policy1 != policy2:
                        #print "\n  (t-test) %s -> %s:" % (policy2, policy1)
                        #t_test(SCORES[policy1], SCORES[policy2])

    else:
        print "\n\n  -{ Scores }-\n"
        results = {True: '(*)', False: ''}
        for policy in sim.scores:
            print "%s: %d %s" % (policy, sim.scores[policy], results[sim.reached_goal[policy]])

    if '-dumppunt' in settings:
        print "\nPOP Policy could have reached the goal (and failed) %d / %d times.\n" % (POP_COULDA, POP_FAILED)
    else:
        print "\n"


def do_policy(domain_file, problem_file, out_directory, popf):

    if not os.path.exists(out_directory):
        os.mkdir(out_directory)

    os.system("cp %s %s" % (domain_file, out_directory))
    os.system("cp %s %s" % (problem_file, out_directory))

    FF_out = os.path.join(out_directory, 'FF.out')
    POPF_out = os.path.join(out_directory, 'POPF.out')
    timings_file = os.path.join(out_directory, 'stats.txt')
    policy_file = os.path.join(out_directory, 'policy.txt')

    time_start = time.time()
    last = time_start

    if popf:
        # Run the POPF planner
        print "\nRunning POPF...\n\n"
        os.system("popf %s %s > %s" % (domain_file, problem_file, POPF_out))
        time_popf = time.time() - last
        last = time.time()

        # Run the lifter to get the POP
        print "\nRunning the lifter...\n\n"
        pop = make_layered_POP(domain_file, problem_file, POPF_out)
        print pop
        print "\n\n"

        # Make a fake FF output
        serial_plan = linearize(pop, 1)[0][1:-1]

        fftext = "found legal plan\n"
        fftext += "\n".join([" : %s %s" % (item.operator, ' '.join(item.arguments)) for item in serial_plan])
        fftext += "\ntime spent\n"

        write_file(FF_out, fftext)

        time_pop = time.time() - last
        last = time.time()

    else:
        # Run FF to get the output
        print "\nRunning FF...\n\n"
        os.system("ff -o %s -f %s > %s" % (domain_file, problem_file, FF_out))
        time_ff = time.time() - last
        last = time.time()

        # Run the lifter to get the POP
        print "\nRunning the lifter...\n\n"
        pop = lift_POP(domain_file, problem_file, FF_out)
        print pop
        print "\n\n"
        time_pop = time.time() - last
        last = time.time()

    # Count the linearizations
    print "\nCounting the number of linearizations...\n\n"
    lin_count = count_linearizations(pop)
    time_count = time.time() - last
    last = time.time()
    if 1 == lin_count:
        print "  !! Warning !! -> No lifting of the POP was possible.\n"
    else:
        print "...found %d linearizations.\n\n" % lin_count

    # Check the causal independence
    print "\nChecking the causal independence...\n\n"
    causal_count = pop.analyze_independence()
    time_causal = time.time() - last
    last = time.time()
    if 0 == causal_count:
        print "  !! Warning !! -> POP exhibits causal independence.\n"
    else:
        print "...found %d causal dependencies.\n\n" % causal_count

    # Run the regresser to get the regression list
    print "\nRunning regresser...\n\n"
    rl, mapping = build_regression_list(pop)
    time_regression = time.time() - last
    last = time.time()

    # Generate the policy
    print "\nComputing the policy...\n\n"
    policy = generate_policy(rl, mapping)
    time_policy = time.time() - last
    last = time.time()

    # Check if the successor generator policy is any better...
    # Run the regresser to get the regression list
    #print "\nRunning regresser...\n\n"
    #rl, mapping = build_regression_list(pop)
    #last = time.time()
    #print "\nComputing the sgpolicy..."
    #generate_sgpolicy(rl, mapping)
    #time_sgpolicy = time.time() - last
    #last = time.time()
    #print "...it took %s time (versus %s for the oadd)\n\n" % (str(time_sgpolicy), str(time_policy))

    # Write the policy
    print "\nWriting the policy...\n\n"
    policy_graph = generate_graph(policy)
    write_file(policy_file, generate_dump(policy, policy_graph))
    (policy_nodes, policy_edges) = generate_stats(policy, policy_graph)
    coverage = compute_coverage(policy, len(pop.F), 0)
    time_dump = time.time() - last
    last = time.time()

    # Write the stats

    STATS = " -{ Time }-\n"
    if popf:
        STATS += "popf=%fs\npop=%fs\ncounting=%fs\ncausal_count=%fs\nregression=%fs\npolicy=%fs\ndump=%fs\ntotal=%fs\n\n" % (time_popf, time_pop, time_count, time_causal, time_regression, time_policy, time_dump, (time.time() - time_start))
    else:
        STATS += "ff=%fs\npop=%fs\ncounting=%fs\ncausal_count=%fs\nregression=%fs\npolicy=%fs\ndump=%fs\ntotal=%fs\n\n" % (time_ff, time_pop, time_count, time_causal, time_regression, time_policy, time_dump, (time.time() - time_start))
    STATS += " -{ Pop }-\n"
    STATS += "Actions: %d\n" % pop.network.number_of_nodes()
    STATS += "Orderings: %d\n" % pop.num_links
    STATS += "Linearizations: %d\n" % lin_count
    STATS += "Causal Count: %d\n\n" % causal_count
    STATS += " -{ Policy }-\n"
    STATS += "Nodes: %d\n" % (policy_nodes)
    STATS += "Edges: %d\n" % (policy_edges)
    STATS += "Coverage: %d\n" % (coverage)

    write_file(timings_file, STATS)

    print "...done!\n"


if __name__ == '__main__':
    myargs, flags = get_opts()

    if 'policy' in flags:
        if ('-domain' not in myargs) or ('-prob' not in myargs) or ('-out' not in myargs):
            print "\n   * Must choose the appropriate settings for policy generation *"
            print USAGE_STRING
            os._exit(1)

        if ('-popf' in myargs) and (myargs['-popf'] == 'yes'):
            popf = True
        else:
            popf = False

        do_policy(myargs['-domain'], myargs['-prob'], myargs['-out'], popf)

    elif 'policyimpact' in flags:
        if ('-domain' not in myargs) or ('-prob' not in myargs) or ('-ffout' not in myargs):
            print "\n   * Must choose the appropriate settings for policy impact *"
            print USAGE_STRING
            os._exit(1)

        do_policy_impact(myargs)

    elif 'simulation' in flags:
        if ('-domain' not in myargs) or ('-prob' not in myargs) or ('-ffout' not in myargs) or ('-policy' not in myargs):
            print "\n   * Must choose the appropriate settings for simulation *"
            print USAGE_STRING
            os._exit(1)

        do_simulation(myargs)

    elif 'analytic' in flags:
        if ('-domain' not in myargs) or ('-prob' not in myargs) or ('-ffout' not in myargs) or ('-policy' not in myargs):
            print "\n   * Must choose the appropriate settings for analytic *"
            print USAGE_STRING
            os._exit(1)

        do_analytic(myargs)

    else:
        print "\n   * Must choose an appropriate task *"
        print USAGE_STRING
        os._exit(1)
