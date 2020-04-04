
from krrt.utils import read_file, get_lines, write_file, match_value
from krrt.planning import parse_output_FF
from krrt.planning.strips.representation import parse_problem, generate_action, Action
from krrt.planning.strips.reasoning import regress_state, progress_state, is_applicable

import random, os, time

class Simulatable(object):
    def get_action(self, is_true_func, lookup):
        assert False, "Error: get_action not implemented!"

    def get_label(self):
        return "UNASSIGNED"

    def reset(self):
        # Do nothing
        pass

class POPPolicy(Simulatable):

    def __init__(self, policy_dump):
        self.nodes = {}
        self.edges = {}
        self.root = None
        self.initialize(policy_dump)

    def get_action(self, is_true, lookup):
        current = self.root
        while 0 != len(self.edges[current]):
            current = self.edges[current][is_true(lookup[self.nodes[current]])]
        return lookup[self.nodes[current]]

    def initialize(self, policy_text):

        num_fluents = policy_text.pop(0)
        self.root = policy_text.pop(0)

        num_nodes = int(policy_text.pop(0))
        for n in range(num_nodes):
            num, val = policy_text.pop(0).split('/')
            self.nodes[num] = val
            self.edges[num] = {}

        num_edges = int(policy_text.pop(0))
        for e in range(num_edges):
            u,v,hl = policy_text.pop(0).split('/')
            self.edges[u][hl == 'h'] = v

    def get_label(self):
        return "POP Policy"


class CurrentStateSerialPolicy(Simulatable):

    def __init__(self, plan, allF, allA, I, G):
        self.current_index = 0
        self.initialize(plan, allF, allA, I, G)

    def reset(self):
        self.current_index = 0

    def entails(self, annotation, is_true):
        for f in annotation:
            if not is_true(f):
                return False
        return True

    def get_action(self, is_true, lookup):

        if not self.entails(self.annotations[self.current_index], is_true):
            return lookup['False']

        self.current_index += 1

        return self.plan[self.current_index-1]

    def initialize(self, plan, allF, allA, I, G):

        new_plan = []

        F = set([])
        A = set([])
        indices = {None: 99999} # Should be larger than any plan we need to deal with
        index = 1

        # Init action
        F |= I

        # Normal actions
        for act in plan.actions:
            a = generate_action(allA[act.operator], act)
            new_plan.append(a)
            F |= a.adds | a.precond | a.dels

        # Goal action
        goal = Action(G, set([]), set([]), "goal")
        F |= goal.precond
        new_plan.append(goal)

        self.plan = new_plan

        annotations = [G]
        current = G
        for act in reversed(new_plan[:-1]):
            current = regress_state(current, act)
            annotations.append(current)

        self.annotations = list(reversed(annotations))

        assert len(self.annotations) == len(self.plan)

    def get_label(self):
        return "Current Annotation"


class AllStateSerialPolicy(CurrentStateSerialPolicy):

    def __init__(self, plan, allF, allA, I, G):
        self.initialize(plan, allF, allA, I, G)

    def get_action(self, is_true, lookup):

        for index in range(len(self.plan) - 1, -1, -1):
            if self.entails(self.annotations[index], is_true):
                return self.plan[index]

        return lookup['False']

    def get_label(self):
        return "Any Annotation"

class SimulationState(object):
    def __init__(self, state, F, settings):
        self.state = state
        self.F = F
        self.settings = settings

    def check_fluent(self, f):
        return f in self.state

    def progress_state(self, action):
        assert is_applicable(self.state, action)
        self.state = progress_state(self.state, action)

    def perturb_state(self, change):
        if 'set' == change[0]:

            self.state |= change[1]
            self.state -= change[2]

        elif 'flip' == change[0]:

            for f in change[1]:
                if f in self.state:
                    self.state.remove(f)
                else:
                    self.state.add(f)

        else:
            print "Error: Unknown change type, %s" % str(change[0])
            import os
            os.sys.exit(1)



class Simulation(object):
    def __init__(self, settings):

        if '-perturber' not in settings:
            self.perturber = perturb_none

        else:
            if 'none' == settings['-perturber']:
                self.perturber = perturb_none
            elif 'prob' == settings['-perturber']:
                self.perturber = perturb_prob
            elif 'probharmful' == settings['-perturber']:
                self.perturber = perturb_prob
                settings['-dynamics'] = 'demonic'
            elif 'probhelpful' == settings['-perturber']:
                self.perturber = perturb_prob
                settings['-dynamics'] = 'angelic'
            elif 'fritz' == settings['-perturber']:
                if 'demonic' == settings['-dynamics']:
                    self.perturber = perturb_fritz_harmful
                else:
                    self.perturber = perturb_fritz
            elif 'fritzharmful' == settings['-perturber']:
                self.perturber = perturb_fritz_harmful
            else:
                print "Error: Invalid perturber, %s" % settings['-perturber']
                return

        self.F = settings['F']
        self.A = settings['A']
        self.I = settings['I']
        self.G = settings['G']

        self.relevant_F = set()
        relevant_F_names = set()
        unachievable_F = set()

        self.lookup = {}

        for action in self.A:
            self.lookup[str(action)] = action
            self.relevant_F |= action.adds
            relevant_F_names |= set([f.name.split(' ')[0] for f in action.adds])

        for fluent in self.F:
            self.lookup[str(fluent)] = fluent

            if (fluent not in self.relevant_F) and (fluent.name.split(' ')[0] in relevant_F_names):
                unachievable_F.add(fluent)
                self.relevant_F.add(fluent)

        self.lookup['False'] = False

        self.policies = {}
        self.states = {}
        self.scores = {}
        self.reached_goal = {}
        self.going = set()
        self.step = 0
        self.computed_domain = None

        self.settings = settings

        if 'yes' == self.settings['-relevant']:
            print "Irrelevant facts removed:"
            for f in self.F - self.relevant_F:
                print "- %s" % str(f)
            print ""
            print "Unachievable facts that are left in:"
            for f in unachievable_F:
                print "- %s" % str(f)
            print ""


    def reset(self):

        for policy in self.policies:
            self.states[policy] = SimulationState(self.I, self.F, self.settings)
            self.going.add(policy)
            self.policies[policy].reset()

        self.step = 0
        self.POP_could_have_reached_goal = False

    def add_policy(self, policy):
        self.policies[policy.get_label()] = policy

    def compute_reduced_domain(self):
        if self.computed_domain:
            return self.computed_domain

        preamble = get_lines(self.settings['-domain'], upper_bound = '.*\(:action.*')

        mid_section = read_file(self.settings['-domain'])[len(preamble):]
        accepting = False
        new_mid_section = []
        for line in mid_section:
            if ':action' in line:
                accepting = False
                for act in self.A:
                    if act.operator in line:
                        accepting = True
            if accepting:
                new_mid_section.append(line)

        if not accepting:
            new_mid_section.append(")")

        self.computed_domain = preamble + new_mid_section
        return self.computed_domain

    def check_initial_state(self, state):

        # Create the new initial state
        preamble = get_lines(self.settings['-prob'], upper_bound = '.*\(:init.*')
        postamble_size = len(get_lines(self.settings['-prob'], lower_bound = '.*\(:goal.*')) + 1
        postamble = read_file(self.settings['-prob'])[-postamble_size:]

        new_init = ['(:init']
        for f in state:
            new_init.append("    %s" % str(f))
        new_init.append(")")

        new_prob = preamble + new_init + postamble

        # Create the new domain (?)
        if True:
            new_domain = self.compute_reduced_domain()
        else:
            new_domain = read_file(self.settings['-domain'])

        # Place the files in the proper place
        cur_time = time.time()
        dom_file = os.path.join(self.settings['-dumppunt'], "%f.dom.pddl" % cur_time)
        prob_file = os.path.join(self.settings['-dumppunt'], "%f.prob.pddl" % cur_time)
        out_file = os.path.join(self.settings['-dumppunt'], "%f.ff.pddl" % cur_time)

        write_file(dom_file, new_domain)
        write_file(prob_file, new_prob)

        # Solve the problem
        os.system("ff -o %s -f %s > %s" % (dom_file, prob_file, out_file))

        # Check if plan exists
        return not match_value(out_file, '.* No plan will solve it.*')

    def do_step(self):

        for policy in self.policies:

            if policy in self.going:

                next_action = self.policies[policy].get_action(self.states[policy].check_fluent, self.lookup)

                if next_action is self.lookup['False']:
                    self.scores[policy] = self.step
                    self.reached_goal[policy] = False
                    self.going.remove(policy)

                    if '-dumppunt' in self.settings and policy == "POP Policy":
                        if self.check_initial_state(self.states[policy].state):
                            self.POP_could_have_reached_goal = True
                        else:
                            self.POP_could_have_reached_goal = False

                # We still need this check in case a state perturbation caused the goal to suddenly be satisfied.
                elif str(next_action) == '(goal)':
                    self.scores[policy] = self.step
                    self.reached_goal[policy] = True
                    self.going.remove(policy)

                else:

                    self.states[policy].progress_state(next_action)

                    # If the policy has reached the goal, we're done.
                    if self.states[policy].state >= self.G:
                        self.scores[policy] = self.step
                        self.reached_goal[policy] = True
                        self.going.remove(policy)

        self.step += 1


    def perturb(self):
        # Get the change
        if 'yes' == self.settings['-relevant']:
            change = self.perturber(self.relevant_F, self.settings)
        else:
            change = self.perturber(self.F, self.settings)

        # Then apply it to all states
        for policy in self.going:
            self.states[policy].perturb_state(change)



#######################
# Perturbing Policies #
#######################
def perturb_none(F, settings):
    return ['flip', []]

def perturb_fritz(F, settings):
    return ['flip', [random.choice(list(F))]]

def perturb_fritz_harmful(F, settings):
    return ['set', set(), set([random.choice(list(F))])]

def perturb_prob(F, settings):

    if '-perprob' in settings:
        prob = float(settings['-perprob'])
    else:
        prob = 0.5

    if '-permax' in settings:
        max_per = int(settings['-permax'])
        F = list(F)
        random.shuffle(F)
    else:
        max_per = -1

    toAdd = set()
    toDel = set()
    count = 0

    for f in F:
        if random.random() < prob:
            count += 1
            if 'angelic' == settings['-dynamics']:
                toAdd.add(f)
            elif 'demonic' == settings['-dynamics']:
                toDel.add(f)
            else:
                if random.choice([True, False]):
                    toAdd.add(f)
                else:
                    toDel.add(f)

            if count == max_per:
                return ['set', toAdd, toDel]

    return ['set', toAdd, toDel]


#####################################
## Interactive / Manual Simulation ##
#####################################
class ManualSimulation(object):
    def __init__(self, pop, pol):
        self.pop = pop
        self.policy = pol
        self.time = 0.0
        self.state = pop.I

    def pause(self, t):
        self.time += t

    def execute(self, a):
        assert is_applicable(self.state, a)
        self.state = progress_state(self.state, a)
        self.policy.add_action(self.time, a)

    def query(self):
        return self.policy.get_action(self.time, self.state)

def simulate_file(pol, filename, Amap, Fmap):
    lines = get_lines(filename, "start simulation", "end simulation")
    num_cases = int(lines.pop(0))

    for sim_num in range(num_cases):
        num_commands = int(lines.pop(0))
        print "\n\n   -{ Simulation %d }-" % (sim_num+1)
        simulate(pol, [lines.pop(0) for i in range(num_commands)], Amap, Fmap)


def simulate(pol, commands, Amap, Fmap):
    pol.reset()
    for cmd in commands:
        (desc, command) = cmd.split(':')
        print "\n%s (%s)" % (desc, command)
        if 'A' == command[0]:
            time = float(command.split('/')[1])
            action = Amap[command.split('/')[2]]
            pol.add_action(time, action)
        elif 'G' == command[0]:
            time = float(command.split('/')[1])
            state = set(map(Fmap.get, command.split('/')[2].split(' ')))
            res = pol.get_action(time, state)
            if res is None:
                res = "Nothing"
            else:
                res = "Execute %s within [%.2f,%.2f]" % (str(res[0]), res[1], res[2])
            print "  Do: %s" % res
        else:
            print "Error: Unknown Command -- %s" % cmd

