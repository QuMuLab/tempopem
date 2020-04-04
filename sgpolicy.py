
from operator import itemgetter
import networkx as nx

NODE_COUNT = 0

def generate_sg(S):
    valid_suffixes, S = separate_finished(S)
    if 0 == len(S):
        return LeafNode(valid_suffixes)

    best_fluent = get_best_fluent(S)

    L, R = partition(S, best_fluent)

    return SwitchNode(best_fluent, valid_suffixes, generate_sg(L), generate_sg(R))

def partition(S, fluent):
    L = []
    R = []
    for (prec, act, suff, cost) in S:
        if fluent in prec:
            L.append((prec - set([fluent]), act, suff, cost))
        else:
            R.append((prec - set([fluent]), act, suff, cost))
    return L,R

def separate_finished(S):
    done = []
    undone = []
    for (prec, act, suff, cost) in S:
        if 0 == len(prec):
            done.append((act, suff, cost))
        else:
            undone.append((prec, act, suff, cost))
    return done, undone

def get_best_fluent(S):
    scores = {}
    for (prec, act, suff, cost) in S:
        for f in prec:
            scores[f] = scores.get(f, 0) + 1
    return sorted(scores.items(), key=itemgetter(1))[0][0]

class PolicyNode(object):
    def __init__(self):
        global NODE_COUNT
        NODE_COUNT += 1


class SwitchNode(PolicyNode):
    def __init__(self, fluent, valid_suffixes, holds, always):
        PolicyNode.__init__(self)
        self.holds = holds
        self.always = always
        self.fluent = fluent
        self.valid_suffixes = valid_suffixes

    def __str__(self):
        return "switch %s\nvalid: %s\nholds:\n%s\nalways\n%s" % (str(self.fluent), str(self.valid_suffixes), str(self.holds), str(self.always))

    def evaluate(self, state, items):

        items.extend(self.valid_suffixes)

        self.always.evaluate(state, items)

        if self.fluent in state:
            self.holds.evaluate(state, items)


class LeafNode(PolicyNode):
    def __init__(self, valid_suffixes):
        PolicyNode.__init__(self)
        self.valid_suffixes = valid_suffixes

    def __str__(self):
        return str(self.valid_suffixes)

    def evaluate(self, state, items):
        items.extend(self.valid_suffixes)


def generate_sgpolicy(reg_list, mapping, quality_func=None):

    quality_func = quality_func or quality_func_min_idle

    S = []
    for r in reg_list:
        for suffix in r:
            for ps in mapping[suffix]:
                S.append((ps.prec, ps.candidate, suffix, quality_func(suffix, ps.candidate)))

    print "\nContexts: %d\n" % len(S)
    pol = generate_sg(S)
    print "\nNodes used: %d\n" % NODE_COUNT

    return pol


#########################
##                     ##
##  Quality functions  ##
##                     ##
#########################
def quality_func_action_count(suffix, candidate):
    return len(suffix.actions)

def quality_func_time_estimate(suffix, candidate):
    return (suffix.goal_estimates[candidate], len(suffix.actions))

def quality_func_min_idle(suffix, candidate):
    return (len(suffix.actions), -1 * suffix.goal_estimates[candidate])
