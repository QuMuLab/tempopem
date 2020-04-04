from krrt.stats.plots import plot
from krrt.utils import load_CSV, get_value, get_opts
from domains import DOMAINS, GOOD_DOMAINS
import os

USAGE_STRING = """
Usage: python analyze.py <TASK> -parameter <value> ...

        Where <TASK> may be:
          rangep: Generate the plot for varying p. (-csv <path to csv file>)
          framework: Check the framework timings. (-domain <domain name> -popf <yes/no>)
          countlinears: Output the number of linearizations for each problem in -domain.
          linearcoverage: Graph the relation between linearizations and coverage ratio.
          linearsimulation: Graph the relation between linearizations and simulation score. (-prob -permax -basedir)

        """

def get_linears(domain):
    from run_all import filter_solved_domains
    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    mapping = {}

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        stat_file = "%s/%s/stats.txt" % (domain, prob_name)
        mapping[prob_name] = get_value(stat_file, '.*Linearizations: (\d+).*', int)

    return mapping

def do_count_linears(domain):
    linear_mapping = get_linears(domain)

    for prob in linear_mapping.keys():
        print "%s,%d" % (prob, linear_mapping[prob])


def do_rangep(csv_file):
    alldata = load_CSV(csv_file)

    data = {}

    for line in alldata[1:]:
        if line[0] != '0' and line[1] != '0':
            if line[-1] not in data:
                data[line[-1]] = [[float(line[0])],[float(line[1])]]
            else:
                data[line[-1]][0].append(float(line[0]))
                data[line[-1]][1].append(float(line[1]))

    xs = []
    ys = []
    ps = []

    for p in sorted(data.keys()):
        xs.append(data[p][0])
        ys.append(data[p][1])
        ps.append(str(p))

    plot(xs, ys, "Fritz Policy", "POP Policy", x_log=False, y_log=False, names=ps, graph_name="Problems Solved (out of 1000)", legend_name="Fluent Change Prob")

def do_linear_vs_coverage():
    from run_all import get_coverage

    xs = []
    ys = []
    ps = []

    for dom in GOOD_DOMAINS:

        lin_mapping = get_linears(dom)
        cov_mapping = get_coverage(dom)

        probs = sorted(list(lin_mapping.keys()))

        xs.append([])
        ys.append([])
        ps.append(dom)

        for prob in probs:
            xs[-1].append(float(lin_mapping[prob]))
            ys[-1].append(float(cov_mapping[prob]))

    plot(xs, ys, "Linearizations", "Coverage Ratio", x_log=True, y_log=False, names=ps, graph_name="Linearizations -vs- Coverage", legend_name="Domain")

    print "Linearizations,Coverage Ratio,Domain"
    for i in range(len(xs)):
        for j in range(len(xs[i])):
            print "%f,%f,%s" % (xs[i][j], ys[i][j], ps[i])


def do_linear_vs_simulation(prob, permax, basedir):

    from run_all import filter_solved_domains

    xs = []
    ys = []
    ps = []

    for dom in GOOD_DOMAINS:

        lin_mapping = get_linears(dom)

        sim_data = filter(lambda x: x[2] == prob, load_CSV("%s/%s_permax%s.csv" % (basedir, dom, permax)))

        dom_probs = filter_solved_domains(dom, DOMAINS[dom])

        probs = [item[1].split('/')[-1].split('.')[0] for item in dom_probs]

        xs.append([])
        ys.append([])
        ps.append(dom)

        for i in range(len(probs)):
            xs[-1].append(float(lin_mapping[probs[i]]))

            if 0.0 == float(sim_data[i][0]):
                ys[-1].append(1.0)
            else:
                ys[-1].append(float(sim_data[i][1]) / float(sim_data[i][0]))

    plot(xs, ys, "Linearizations", "Simulation Ratio", x_log=True, y_log=False, names=ps, graph_name="Linearizations -vs- Simulation (p = %s)" % prob, legend_name="Domain", xyline = False)



def do_framework(domain, popf):
    from run_all import filter_solved_domains
    dom_probs = filter_solved_domains(domain, DOMAINS[domain])

    t_planner = 0.0
    t_pop = 0.0
    t_counting = 0.0
    t_causal_count = 0.0
    t_regression = 0.0
    t_policy = 0.0
    t_dump = 0.0
    t_total = 0.0

    for (dom, prob) in dom_probs:
        prob_name = prob.split('/')[-1].split('.')[0]
        stat_file = "%s/%s/stats.txt" % (domain, prob_name)
        if popf:
            t_planner += get_value(stat_file, '.*popf=([0-9]+\.?[0-9]+)s.*', float)
        else:
            t_planner += get_value(stat_file, '.*ff=([0-9]+\.?[0-9]+)s.*', float)
        t_pop += get_value(stat_file, '.*pop=([0-9]+\.?[0-9]+)s.*', float)
        t_counting += get_value(stat_file, '.*counting=([0-9]+\.?[0-9]+)s.*', float)
        t_causal_count += get_value(stat_file, '.*causal_count=([0-9]+\.?[0-9]+)s.*', float)
        t_regression += get_value(stat_file, '.*regression=([0-9]+\.?[0-9]+)s.*', float)
        t_policy += get_value(stat_file, '.*policy=([0-9]+\.?[0-9]+)s.*', float)
        t_dump += get_value(stat_file, '.*dump=([0-9]+\.?[0-9]+)s.*', float)
        t_total += get_value(stat_file, '.*total=([0-9]+\.?[0-9]+)s.*', float)

    print "\n%2.2f%% \t Planner" % (100 * t_planner / t_total)
    print "%2.2f%% \t POP Lifting" % (100 * t_pop / t_total)
    print "%2.2f%% \t Counting Linearizations" % (100 * t_counting / t_total)
    print "%2.2f%% \t Counting Causal Actions" % (100 * t_causal_count / t_total)
    print "%2.2f%% \t Computing Regression List" % (100 * t_regression / t_total)
    print "%2.2f%% \t Computing Policy" % (100 * t_policy / t_total)
    print "%2.2f%% \t Writing the Policy\n" % (100 * t_dump / t_total)

if __name__ == '__main__':
    myargs, flags = get_opts()

    if 'rangep' in flags:
        if '-csv' not in myargs:
            print "Error: Must choose a csv file:"
            print USAGE_STRING
            os._exit(1)

        do_rangep(myargs['-csv'])

    elif 'framework' in flags:
        if '-domain' not in myargs:
            print "Error: Must choose a domain:"
            print USAGE_STRING
            os._exit(1)

        if ('-popf' in myargs) and (myargs['-popf'] == 'yes'):
            do_framework(myargs['-domain'], True)
        else:
            do_framework(myargs['-domain'], False)

    elif 'countlinears' in flags:
        if '-domain' not in myargs:
            print "Error: Must choose a domain:"
            print USAGE_STRING
            os._exit(1)

        do_count_linears(myargs['-domain'])

    elif 'linearcoverage' in flags:
        do_linear_vs_coverage()

    elif 'linearsimulation' in flags:
        if ('-basedir' not in myargs) or ('-prob' not in myargs) or ('-permax' not in myargs):
            print "Error: Must supply basedir, probability, and permax:"
            print USAGE_STRING
            os._exit(1)

        do_linear_vs_simulation(myargs['-prob'], myargs['-permax'], myargs['-basedir'])

    else:
        print USAGE_STRING

