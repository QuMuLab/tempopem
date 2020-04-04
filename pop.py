
import networkx as nx

from krrt.planning.strips.representation import Action, Fluent
from krrt.utils import read_file

def create_serial_pop(plan):
    pop = POP()
    for action in plan:
        pop.add_action(action)

    for i in range(len(plan) - 1):
        pop.link_actions(plan[i], plan[i+1], 'serial')

    return pop

class POP(object):

    def __init__(self):
        self.network = nx.DiGraph()
        self.num_links = 0
        self.init = None
        self.goal = None
        self.A_map = {}
        self.follow_constraints = set()
        self.follow_constraints_rhs_map = {}

    def add_action(self, a):
        self.network.add_node(a)

        if a.operator == 'init':
            self.init = a
        if a.operator == 'goal':
            self.goal = a

        self.A_map[a.operator] = a

    def set_temporal_constraint(self, a1, a2, l, u, enf=None, frc=None):

        if self.network.has_edge(a1, a2) and 'constraint' in self.network[a1][a2]:
            assert (enf is None) or (enf == self.network[a1][a2]['constraint'].enforce)
            assert (frc is None) or (frc == self.network[a1][a2]['constraint'].forced)

            self.network[a1][a2]['constraint'].l = max(self.network[a1][a2]['constraint'].l, l)
            self.network[a1][a2]['constraint'].u = min(self.network[a1][a2]['constraint'].u, u)

            assert self.network[a1][a2]['constraint'].l <= self.network[a1][a2]['constraint'].u

        else:
            c = TemporalConstraint(a1, a2, l, u, forced=frc, enforce=enf)
            self.link_actions(a1, a2, c.label)
            self.network[a1][a2]['constraint'] = c

            if frc == TemporalConstraint.FORCE_FOLLOW:
                self.follow_constraints.add(c)
                if a2 not in self.follow_constraints_rhs_map:
                    self.follow_constraints_rhs_map[a2] = set()
                self.follow_constraints_rhs_map[a2].add(c)

    def link_actions(self, a1, a2, reason):
        if self.network.has_edge(a1, a2):
            self.network[a1][a2]['reasons'].add(reason)
        else:
            self.network.add_edge(a1, a2, reasons = set([reason]))
        self.num_links += 1

    def load_constraint_graph(self, filename, actions):

        self.network = nx.DiGraph()
        self.num_links = 0

        G = nx.read_gml(filename)

        for n in G:
            self.add_action(actions[G.node[n]['label'][1:-1]])

        for n1 in G:
            for n2 in G[n1]:
                l = TemporalConstraint.gen_val(G[n1][n2]['label'].split(',')[0][1:])
                u = TemporalConstraint.gen_val(G[n1][n2]['label'].split(',')[1][:-1])
                a1 = actions[G.node[n1]['label'][1:-1]]
                a2 = actions[G.node[n2]['label'][1:-1]]
                self.set_temporal_constraint(a1, a2, l, u)

    def load_custom_pop(self, filename):
        # ######################
        #
        #     File format
        #
        # ###################
        #
        # fluent1 fluent2 ...
        # init_fluent1 init_fluent2 ...
        # goal_fluetn1 goal_fluent2 ...
        # <num actions>
        # action1/pre1 pre2/add1 add2/del1 del2
        # ...
        # <num constraints>
        # <E/A/P/F/O>/a1/a2/l/u
        # ...
        # <num durative actions>
        # <SD/ED>/action1/l/u
        # ...

        lines = read_file(filename)

        fluents = dict([(f,Fluent(f)) for f in lines.pop(0).split()])
        self.F_map = fluents

        self.I = set(map(fluents.get, lines.pop(0).split()))
        self.G = set(map(fluents.get, lines.pop(0).split()))

        #self.free_fluent = Fluent("agent_free")
        #self.F_map['agent_free'] = self.free_fluent
        #self.I.add(self.free_fluent)
        #self.G.add(self.free_fluent)

        init = Action(set(), self.I, set(), "init")
        goal = Action(self.G, set(), set(), "goal")

        self.add_action(init)
        self.add_action(goal)

        num_actions = int(lines.pop(0))
        allA = {'init':init, 'goal':goal}
        for i in range(num_actions):
            (act_name, pres, adds, dels) = lines.pop(0).split('/')
            #a = Action(set(map(fluents.get, pres.split())) | set([self.free_fluent]),
            #           set(map(fluents.get, adds.split())) | set([self.free_fluent]),
            #           set(map(fluents.get, dels.split())),
            #           act_name)
            a = Action(set(map(fluents.get, pres.split())),
                       set(map(fluents.get, adds.split())),
                       set(map(fluents.get, dels.split())),
                       act_name)
            allA[act_name] = a
            self.add_action(a)
            self.link_actions(init, a, 'init')
            self.link_actions(a, goal, 'goal')

        num_constraints = int(lines.pop(0))
        enf_map = {'E': [TemporalConstraint.ENFORCE_EXISTS, TemporalConstraint.FORCE_LEAD],
                   'A': [TemporalConstraint.ENFORCE_FORALL, TemporalConstraint.FORCE_LEAD],
                   'P': [TemporalConstraint.ENFORCE_RECENT, TemporalConstraint.FORCE_LEAD],
                   'F': [TemporalConstraint.ENFORCE_RECENT, TemporalConstraint.FORCE_FOLLOW]}
        for i in range(num_constraints):
            (enforce, a1, a2, l, u) = lines.pop(0).split('/')
            if 'O' == enforce:
                self.link_actions(allA[a1], allA[a2], "ordering")
            else:
                self.set_temporal_constraint(allA[a1], allA[a2], l, u, enf_map[enforce][0], enf_map[enforce][1])

        num_durative_actions = int(lines.pop(0))
        for i in range(num_durative_actions):
            (variation, act_name, l, u) = lines.pop(0).split('/')
            self.make_durative_action(variation, allA[act_name], TemporalConstraint.gen_val(l), TemporalConstraint.gen_val(u))


    def print_constraint_graph(self, location):
        # Fix the labels so gephi can read them
        for e in self.network.edges_iter():
            if 'constraint' in self.network.edge[e[0]][e[1]]:
                self.network.edge[e[0]][e[1]]['label'] = self.network.edge[e[0]][e[1]]['constraint'].label
            else:
                self.network.edge[e[0]][e[1]]['label'] = ''

        # Dump the graph
        nx.write_dot(self.network, location)

    def print_reason_graph(self, location):
        # Fix the labels so gephi can read them
        for e in self.network.edges_iter():
            self.network.edge[e[0]][e[1]]['label'] = ' / '.join(map(str, self.network.edge[e[0]][e[1]]['reasons']))

        # Dump the graph
        nx.write_dot(self.network, location)

    def unlink_actions(self, a1, a2, reason):
        self.network[a1][a2]['reasons'].remove(reason)

        if 0 == len(self.network[a1][a2]['reasons']):
            self.network.remove_edge(a1, a2)
        self.num_links -= 1

    def remove_action(self, a):

        for (pre, _) in self.network.in_edges(a):
            if ('constraint' in self.network[pre][a]) and \
               (self.network[pre][a]['constraint'].forced == TemporalConstraint.FORCE_FOLLOW):
                self.follow_constraints.remove(self.network[pre][a]['constraint'])

            self.num_links -= len(self.network[pre][a]['reasons'])
            self.network.remove_edge(pre, a)

        for (_, post) in self.network.out_edges(a):
            if ('constraint' in self.network[a][post]) and \
                           (self.network[a][post]['constraint'].forced == TemporalConstraint.FORCE_FOLLOW):
                            self.follow_constraints.remove(self.network[a][post]['constraint'])

            self.num_links -= len(self.network[a][post]['reasons'])
            self.network.remove_edge(a, post)

        self.network.remove_node(a)

    def analyze_independence(self):

        causal_dependent_count = 0
        reachability = nx.all_pairs_shortest_path(self.network)

        for a1 in self.network.nodes():
            for a2 in self.network.nodes():
                if (a2 not in reachability[a1]) and (a1 not in reachability[a2]):
                    if a1.adds & a2.precond:
                        causal_dependent_count += len(a1.adds & a2.precond)
                        #print "%s can add %s for %s" % (str(a1), str(a1.adds & a2.precond), str(a2))

        return causal_dependent_count

    def make_all_connections(self, start, end, _l=None, _u=None):
        _l = _l or TemporalConstraint.epsilon
        _u = _u or TemporalConstraint.infinity

        l = {True: _l, False: lambda: _l}[callable(_l)]
        u = {True: _u, False: lambda: _u}[callable(_u)]

        starts = filter(lambda x: start in str(x), self.network.nodes())
        ends = filter(lambda x: end in str(x), self.network.nodes())

        for s in starts:
            for e in ends:
                self.set_temporal_constraint(s, e, l(), u())

    def make_durative_operator(self, op_name, _l=None, _u=None):
        _l = _l or TemporalConstraint.epsilon
        _u = _u or TemporalConstraint.infinity

        l = {True: _l, False: lambda: _l}[callable(_l)]
        u = {True: _u, False: lambda: _u}[callable(_u)]

        for n in self.network.nodes():
            if op_name in str(n):
                self.make_durative_action('ED', n, l(), u())

    def make_durative_action(self, variation, action, l=None, u=None):
        l = l or TemporalConstraint.epsilon
        u = u or TemporalConstraint.infinity
        assert action in self.network

        # Create a connecting fluent
        fa = Fluent("exec_%s" % str(action)[1:-1].replace(' ', '_'))
        fn = Fluent("noexec_%s" % str(action)[1:-1].replace(' ', '_'))

        # Add the start and end actions
        #start = Action(action.precond | set([fn]), set([fa]), set([fn, self.free_fluent]), "startA_%s" % str(action)[1:-1])
        if 'SD' == variation:
            start = Action(action.precond | set([fn]), set([fa]), action.dels | set([fn]), "startA_%s" % str(action)[1:-1])
            end = Action(set([fa]), action.adds | set([fn]), set([fa]), "endA_%s" % str(action)[1:-1])
        elif 'ED' == variation:
            start = Action(action.precond | set([fn]), set([fa]), set([fn]), "startA_%s" % str(action)[1:-1])
            end = Action(set([fa]), action.adds | set([fn]), action.dels | set([fa]), "endA_%s" % str(action)[1:-1])
        else:
            assert False, "Error: Unknown durative action variation -- %s" % variation

        self.add_action(start)
        self.add_action(end)
        self.init.addAdd(fn)
        self.goal.addPrecond(fn)

        self.F_map[fa.name] = fa
        self.F_map[fn.name] = fn

        # Add the links and constraints
        self.set_temporal_constraint(start, end, l, u)

        for (n,_) in self.network.in_edges(action):
            for reason in self.network.edge[n][action]['reasons']:
                self.link_actions(n, start, reason)
            if 'constraint' in self.network.edge[n][action]:
                self.set_temporal_constraint(n, start,
                                             self.network.edge[n][action]['constraint'].l,
                                             self.network.edge[n][action]['constraint'].u,
                                             self.network.edge[n][action]['constraint'].enforce,
                                             self.network.edge[n][action]['constraint'].forced)

        for (_,n) in self.network.out_edges(action):
            for reason in self.network.edge[action][n]['reasons']:
                self.link_actions(end, n, reason)
            if 'constraint' in self.network.edge[action][n]:
                self.set_temporal_constraint(end, n,
                                             self.network.edge[action][n]['constraint'].l,
                                             self.network.edge[action][n]['constraint'].u,
                                             self.network.edge[action][n]['constraint'].enforce,
                                             self.network.edge[action][n]['constraint'].forced)

        # Remove the old stuff
        self.remove_action(action)


    def __str__(self):
        return "POP with %d actions and %d causal links / ordering constraints" % (self.network.number_of_nodes(), self.num_links)

    def __repr__(self):
        return self.__str__()


class TemporalConstraint(object):

    infinity = float('inf')
    epsilon = 0.00001

    FORCE_LEAD = 0
    FORCE_FOLLOW = 1
    FORCE_MUTUAL = 2
    FORCE_NONE = 3

    ENFORCE_EXISTS = 0
    ENFORCE_FORALL = 1
    ENFORCE_RECENT = 2

    @staticmethod
    def gen_val(val):
        if 'eps' == val:
            return TemporalConstraint.epsilon
        elif 'inf' == val:
            return TemporalConstraint.infinity
        else:
            return float(val)

    def __init__(self, s, t, l=None, u=None, forced=None, enforce=None, pop=None, trivial_anchors=False):

        # Trivial anchors is false when we've attached constraints to a_I or a_G
        self.trivial_anchors = trivial_anchors

        if isinstance(l, str):
            l = TemporalConstraint.gen_val(l)
        if isinstance(u, str):
            u = TemporalConstraint.gen_val(u)

        self.l = l or self.epsilon
        self.u = u or self.infinity

        self.forced = forced or self.FORCE_LEAD
        self.enforce = enforce or self.ENFORCE_RECENT

        # Don't allow unforced following for now
        assert self.forced != self.FORCE_NONE
        # Make sure we don't contradict an exists
        assert (self.forced != self.FORCE_NONE) or (self.enforce != self.ENFORCE_EXISTS)
        # If forced following is used, then make sure recent is enforced
        assert (self.forced != self.FORCE_FOLLOW) or (self.enforce == self.ENFORCE_RECENT)

        # Handle mutual forcing with auxillery fluents
        if self.forced == self.FORCE_MUTUAL:
            # Make sure the mutual is done with recent
            assert self.enforce == self.ENFORCE_RECENT
            assert pop is not None

            fa = Fluent(("active_%s_%s" % (str(s)[1:-1], str(t)[1:-1])).replace(' ', '_'))
            fn = Fluent(("notactive_%s_%s" % (str(s)[1:-1], str(t)[1:-1])).replace(' ', '_'))

            s.addPrecond(fn)
            s.addAdd(fa)
            s.addDel(fn)

            t.addPrecond(fa)
            t.addAdd(fn)
            t.addDel(fa)

            pop.init.addAdd(fn)
            pop.goal.addPrecond(fn)

        self.s = s
        self.t = t

    def copy(self, new_s, new_t):
        assert self.forced != TemporalConstraint.FORCE_MUTUAL, "Cannot handle mutual forced forall constraints."
        return TemporalConstraint(new_s, new_t, self.l, self.u, self.forced, self.enforce)

    def edges(self):
        return [(self.s, self.t, {'weight':self.u}), (self.t, self.s, {'weight':-(self.l)})]

    @property
    def label(self):
        prefix = ''
        if (self.ENFORCE_RECENT == self.enforce) and (self.FORCE_FOLLOW == self.forced):
            prefix = '>'
        if (self.ENFORCE_RECENT == self.enforce) and (self.FORCE_LEAD == self.forced):
            prefix = '<'
        return "[%s,%s]%s" % (self.convert_str(self.l), self.convert_str(self.u), prefix)

    @property
    def is_simple(self):
        # #################################
        #
        #  We would like to rule out trivial edges that will not contribute
        #   to tighter bounds during the computation. One sufficient condition
        #   for this is that the upper bound for all of the edges are infinity
        #   and there is no shorter path than the lower bound from the candidate
        #   to the source node. How this can be checked, however, is unclear.
        #   A stronger (sufficient) condition is when self.l == 0.
        #
        #  It should be noted that a node will be fully included if at least
        #   one edge is deamed to be not simple.

        #return (self.l == self.epsilon) and (self.u == self.infinity)
        #return (self.l == (-1 * (self.infinity))) and (self.u == self.infinity)
        #return self.u == self.infinity
        #return (self.l == 0) and (self.u == self.infinity)
        return self.trivial_anchors and ((self.s.operator == 'init') or (self.t.operator == 'goal'))

    def convert_str(self, num):
        if num == self.infinity:
            return 'inf'
        elif num == self.epsilon:
            return 'eps'
        else:
            return str(num)

