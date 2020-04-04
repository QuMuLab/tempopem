
from domains import DOMAINS

from krrt.utils import get_opts, run_experiment, match_value, get_value, load_CSV

import os

USAGE_STRING = """
Usage: python run_all.py <TASK> -domain <domain> ...

        Where <TASK> may be:
          policy: Generate the all the policies from input domain
          analytic: Generate the analytic (state coverage) comparison
          policyimpact: Generate all the policy impact levels for a domain
          helpmax: Generate the simulation results for probhelpful (must specify -permax)
          harmmax: Generate the simulation results for probharmful (must specify -permax)
          random: Generate the simulation results for randomly flipping -permax fluents with probability -prob

        Additional Options:
          relevant: Only use relevant fluents for the simulation
          popf: Do the policy construction with popf

        """

TRIALS = 1000
SHOW_DATA = True


def filter_solved_domains(domain, dom_probs):
    toRet = []
    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        if os.path.exists("%s/%s/policy.txt" % (domain, prob_name)):
            toRet.append((dom, prob))
    return toRet


def do_policy_impact(domain):

    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    print "Problem,Time Increase,Punt Ratio,Avg. Serial Time,Avg. Policy Time"

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        os.system("python executer.py policyimpact -domain %s -prob %s -ffout %s/%s/FF.out > tmp" % (dom, prob, domain, prob_name))
        impact = get_value('tmp', "Fritz approach took ([0-9]+\.?[0-9]+) times longer.", float)
        punt_ratio = get_value('tmp', "Punt Ratio: ([0-9]+\.?[0-9]+)", float)
        avg_serial_time = get_value('tmp', "Avg serial time: ([0-9]+\.?[0-9]+)", float)
        avg_policy_time = get_value('tmp', "Avg policy time: ([0-9]+\.?[0-9]+)", float)

        print "%s,%3.4f,%3.4f,%f,%f" % (prob_name, impact, punt_ratio, avg_serial_time, avg_policy_time)

    os.system('rm tmp')


def get_coverage(domain):

    dom_probs = filter_solved_domains(domain, DOMAINS[domain])
    mapping = {}

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        os.system("python executer.py analytic -domain %s -prob %s -ffout %s/%s/FF.out -policy %s/%s/policy.txt > tmp" % (dom, prob, domain, prob_name, domain, prob_name))
        policy_coverage = get_value('tmp', "POP Policy:\t ([0-9]+)", int)
        fritz_coverage = get_value('tmp', "Fritz Policy:\t ([0-9]+)", int)
        ratio = get_value('tmp', "Ratio: ([0-9]+\.?[0-9]+)", float)

        mapping[prob_name] = ratio

    os.system('rm tmp')

    return mapping

def do_analytic(domain):

    coverage_mapping = get_coverage(domain)

    print "Problem,Ratio"

    for prob in coverage_mapping.keys():
        print "%s,%3.5f" % (prob, coverage_mapping[prob])


def do_random(domain, permax, perprob, relevance):

    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    print "Problem,Current State Success,Any State Success,POP Policy Success,Current Mean Distance,Any Mean Distance,POP Policy Mean Distance"

    final_data = ""

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        sim_name = "simulation_results.%s.%s.%s.rel_%s.csv" % (domain, permax, perprob, relevance.split(' ')[-1])
        os.system("python executer.py simulation -domain %s -prob %s -ffout %s/%s/FF.out -policy %s/%s/policy.txt -perturber prob -permax %s -trials %d -perprob %s %s -simname %s > /dev/null" % (dom, prob, domain, prob_name, domain, prob_name, permax, TRIALS, perprob, relevance, sim_name))
        data = load_CSV(sim_name)
        line  = prob_name + ','
        line += ','.join([data[1][1], data[2][1], data[3][1]]) + ','
        line += ','.join([data[1][2], data[2][2], data[3][2]])
        print line

        final_data += ','.join([str(int(float(data[2][1]) * TRIALS)), str(int(float(data[3][1]) * TRIALS)), perprob]) + "\n"

        os.system("mv %s %s/%s/%s" % (sim_name, domain, prob_name, sim_name))

    if SHOW_DATA:
        print "\n%s" % final_data


def do_probhelpful_permax(domain, permax, relevance):

    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    print "Problem,Current State Success,Any State Success,POP Policy Success,Current Mean Distance,Any Mean Distance,POP Policy Mean Distance"

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        os.system("python executer.py simulation -domain %s -prob %s -ffout %s/%s/FF.out -policy %s/%s/policy.txt -perturber probhelpful -permax %s -trials %d %s > /dev/null" % (dom, prob, domain, prob_name, domain, prob_name, permax, TRIALS, relevance))
        data = load_CSV('simulation_results.csv')
        line  = prob_name + ','
        line += ','.join([data[1][1], data[2][1], data[3][1]]) + ','
        line += ','.join([data[1][2], data[2][2], data[3][2]])
        print line

        os.system("mv simulation_results.csv %s/%s/simulation_helpful_permax%s.csv" % (domain, prob_name, permax))

def do_probharmful_permax(domain, permax, relevance):

    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    print "Problem,Current State Success,Any State Success,POP Policy Success,Current Mean Distance,Any Mean Distance,POP Policy Mean Distance"

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        os.system("python executer.py simulation -domain %s -prob %s -ffout %s/%s/FF.out -policy %s/%s/policy.txt -perturber probharmful -permax %s -trials %d %s > /dev/null" % (dom, prob, domain, prob_name, domain, prob_name, permax, TRIALS, relevance))
        data = load_CSV('simulation_results.csv')
        line  = prob_name + ','
        line += ','.join([data[1][1], data[2][1], data[3][1]]) + ','
        line += ','.join([data[1][2], data[2][2], data[3][2]])
        print line

        os.system("mv simulation_results.csv %s/%s/simulation_harmful_permax%s.csv" % (domain, prob_name, permax))


def do_policy(domain, popf):
    dom_probs = DOMAINS[domain]

    args = ["-domain %s -prob %s -out %s/%s" % (item[0], item[1], domain, item[1].split('/')[-1].split('.')[0]) for item in dom_probs]

    results = run_experiment(
        base_command = "python executer.py policy -popf %s" % popf,
        single_arguments = {'prob': args},
        time_limit = 1800, # 15minute time limit (900 seconds)
        memory_limit = 1000, # 1gig memory limit (1000 megs)
        results_dir = domain,
        progress_file = None,
        processors = 1 # You've got 8 cores, right?
    )

    timeouts = 0
    memouts = 0
    for res_id in results.get_ids():
        result = results[res_id]
        if result.timed_out:
            if match_value(result.output_file, 'MemoryError'):
                memouts += 1
            else:
                timeouts += 1
        os.system("mv %s %s/OUT" % (result.output_file, result.single_args['prob'].split('-out ')[-1]))

    print "\nTimed out %d times." % timeouts
    print "Ran out of memory %d times.\n" % memouts

if __name__ == '__main__':
    myargs, flags = get_opts()

    if '-domain' not in myargs:
        print "Error: Must choose a domain:"
        print USAGE_STRING
        os._exit(1)

    if 'policy' in flags:
        if 'popf' in flags:
            do_policy(myargs['-domain'], 'yes')
        else:
            do_policy(myargs['-domain'], 'no')

    if 'policyimpact' in flags:
        do_policy_impact(myargs['-domain'])

    if 'analytic' in flags:
        do_analytic(myargs['-domain'])

    ###########################
    ## Simulation Techniques ##
    ###########################
    if 'relevant' in flags:
        relevance = '-relevant yes'
    else:
        relevance = '-relevant no'

    if 'helpmax' in flags:
        if '-permax' not in myargs:
            print "Error: Must choose a permax if using helpmax:"
            print USAGE_STRING
            os._exit(1)

        do_probhelpful_permax(myargs['-domain'], myargs['-permax'], relevance)

    if 'harmmax' in flags:
        if '-permax' not in myargs:
            print "Error: Must choose a permax if using harmmax:"
            print USAGE_STRING
            os._exit(1)

        do_probharmful_permax(myargs['-domain'], myargs['-permax'], relevance)

    if 'random' in flags:
        if '-permax' not in myargs:
            print "Error: Must choose a permax if using random:"
            print USAGE_STRING
            os._exit(1)

        if '-prob' not in myargs:
            myargs['-prob'] = 0.5

        do_random(myargs['-domain'], myargs['-permax'], myargs['-prob'], relevance)
