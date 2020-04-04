
from krrt.utils import read_file

import networkx as nx

lines = read_file('translation')
mapping = {}
for l in lines:
    mapping[l.split(' ')[0]] = l.split(' ')[1]

lines = read_file('cog-pop')
action_lines = lines[4:23]
ordering_lines = lines[24:42]
constraint_lines = lines[42:54]
durative_lines = lines[55:66]

def fix(st):
    return '\\_'.join(st.split('_'))    

def dump_action(line):    
    tokens = line.split('/')
    #print "\\begin{align*}"
    print "\\\\"
    print "  %s&:\\\\" % fix(tokens[0])
    if '' == tokens[1]:
        print "  \\langle &\\lbrace \\rbrace,\\\\"
    else:
        print "  \\langle &\\lbrace %s \\rbrace,\\\\" % ', '.join(map(lambda x: fix(mapping[x]), tokens[1].split(' ')))
    
    if '' == tokens[2]:
        print "  &\\lbrace \\rbrace,\\\\"
    else:
        print "  &\\lbrace %s \\rbrace,\\\\" % ', '.join(map(lambda x: fix(mapping[x]), tokens[2].split(' ')))
    
    if '' == tokens[3]:
        print "  &\\lbrace \\rbrace \\rangle\\\\"
    else:
        print "  &\\lbrace %s \\rbrace \\rangle\\\\" % ', '.join(map(lambda x: fix(mapping[x]), tokens[3].split(' ')))
    
    #print "\\end{align*}\n"

def fix_num(st):
    if 'inf' == st:
        return "\\infty"
    elif 'eps' == st:
        return "\\epsilon"
    else:
        return st

def dump_constraint(line):
    tokens = line.split('/')
    cons = '  \\item $'
    if 'P' == tokens[0]:
        cons += "\\customrtc{%s}{%s}{%s}{%s}" % (fix(tokens[1]), fix(tokens[2]), fix_num(tokens[3]), fix_num(tokens[4]))
    elif 'F' == tokens[0]:
        cons += "\\customftc{%s}{%s}{%s}{%s}" % (fix(tokens[1]), fix(tokens[2]), fix_num(tokens[3]), fix_num(tokens[4]))
    else:
        print "Error: " + line
    print cons + "$"

def dump_durative(line):
    tokens = line.split('/')
    print "  \\item $%s \\leq duration(%s) \\leq %s$" % (fix_num(tokens[2]), fix(tokens[1]), fix_num(tokens[3]))


# Action Dump
#for act in action_lines:
#    dump_action(act)

# Goal Dump
#print ', '.join(map(lambda x: fix(mapping[x]), 'f1 f5 f7 f8 f10 f11 f12 f13'.split(' ')))

# Constraint Dump
#for c in constraint_lines:
#    dump_constraint(c)

# Durative Dump
#for d in durative_lines:
#    dump_durative(d)


#stn_plan = [
#['init', 0.000000],
#['wakeup', 420.000000],
#['serve_breakfast', 30.000000],
#['check_full', 15.000005],
#['startA_drive_kids_school', 29.999995],
#['endA_drive_kids_school', 30.000000],
#['startA_drive_mall', 82.499975],
#['endA_drive_mall', 20.000000],
#['check_at_mall', 41.249988],
#['startA_get_groceries', 20.624999],
#['endA_get_groceries', 60.000000],
#['startA_watch_movie', 10.312504],
#['endA_watch_movie', 95.156247],
#['startA_drive_home', 2.578134],
#['endA_drive_home', 20.000000],
#['startA_do_laundry', 1.289067],
#['startA_read_book', 0.644538],
#['endA_do_laundry', 29.999990],
#['check_at_home', 0.322269],
#['endA_read_book', 0.161140],
#['startA_drive_school', 0.080575],
#['endA_drive_school', 20.000000],
#['startA_drive_kids_home', 0.040292],
#['endA_drive_kids_home', 30.000000],
#['startA_clean_kitchen', 80.020136],
#['endA_clean_kitchen', 20.000000],
#['check_clean_kitchen', 30.010073],
#['startA_cook_meal', 25.005032],
#['endA_cook_meal', 17.502516],
#['serve_meal', 3.751268],
#['goto_sleep', 121.875634]
#        ]

#total = 0.0
#for p in stn_plan:
#    total += p[1]
#    print "[%f] %s" % (total, p[0])


# Ordering Dump
G = nx.DiGraph()
for line in ordering_lines:
    tokens = line.split('/')
    G.add_edge(tokens[1], tokens[2])

nx.write_dot(G, 'graph.dot')
