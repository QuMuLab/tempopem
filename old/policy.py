
import networkx as nx

NODE_COUNT = 0

class PolicyNode(object):
    def __init__(self):
        global NODE_COUNT
        NODE_COUNT += 1
        self.high = None
        self.low = None
        self.fluent = None
        self.action = None
        self.parents = []
        self.hash_val = None
        self.score = None

    def is_true(self):
        return (self.action is not None) and (self.action is not False)

    def is_false(self):
        return False == self.action

    def set_high(self, high):
        self.high = high
        high.add_parent(self)

    def set_low(self, low):
        self.low = low
        low.add_parent(self)

    def add_parent(self, p):
        self.parents.append(p)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.id()

    def __cmp__(self, other):
        return self.__hash__() == other.__hash__()

    def __eq__(self, other):
        return self.__cmp__(other)

    def __neq__(self, other):
        return not self.__cmp__(other)

class InnerNode(PolicyNode):
    def __init__(self, fluent):
        PolicyNode.__init__(self)
        self.fluent = fluent

    def label(self):
        return str(self.fluent)

    def id(self):
        if self.hash_val is None:
            self.hash_val = hash("%s/%d/%d" % (str(self.fluent), hash(self.high), hash(self.low)))
        return self.hash_val

    def __str__(self):
        return "(%s: %s / %s)" % (str(self.fluent), str(self.high), str(self.low))

class LeafNode(PolicyNode):
    def __init__(self, action):
        PolicyNode.__init__(self)
        self.action = action
        self.high = self
        self.low = self

    def label(self):
        return str(self.action)

    def id(self):
        if self.hash_val is None:
            self.hash_val = hash(self.label())
        return self.hash_val

    def __str__(self):
        return str(self.action)


FALSE = LeafNode(False)
LOOKUP_TABLE = {} # Maps fg and h to the proper root
NODE_LOOKUP = {} # Maps a node's id to the node itself

def compute_coverage(policy, max_depth, depth):

    if not policy.score:

        if policy.high.__class__ == InnerNode:
            high_score = compute_coverage(policy.high, max_depth, depth+1)
        else:
            if policy.high is not FALSE:
                high_score = 2 ** (max_depth - depth - 1)
            else:
                high_score = 0

        if policy.low.__class__ == InnerNode:
            low_score = compute_coverage(policy.low, max_depth, depth+1)
        else:
            if policy.low is not FALSE:
                low_score = 2 ** (max_depth - depth - 1)
            else:
                low_score = 0

        policy.score = high_score + low_score

    return policy.score

def generate_graph(policy):
    graph = nx.DiGraph()

    nodes = set()

    def build_graph(node):
        if node not in nodes:
            nodes.add(node)
            graph.add_node(node)

            if node.__class__ == InnerNode:
                build_graph(node.high)
                build_graph(node.low)

        if node.high == node.low:
            graph.add_edge(node, node.high, high = -1)
        else:
            graph.add_edge(node, node.high, high = 1)
            graph.add_edge(node, node.low, high = 0)

    build_graph(policy)

    return graph

def generate_dot(policy, graph = None):

    if not graph:
        graph = generate_graph(policy)

    dot_string = "\ndigraph Policy {\n"

    for node in graph.nodes():
        dot_string += "    %d [label=\"%s\"];\n" % (hash(node), node.label())

    for (u,v) in graph.edges():
        if hash(u) != hash(v):

            is_high = graph.get_edge_data(u,v)['high']

            if 0 != is_high:
                dot_string += "    %d -> %d;\n" % (hash(u), hash(v))
            if 1 != is_high:
                dot_string += "    %d -> %d [style=dotted];\n" % (hash(u), hash(v))

    dot_string += "}\n"

    return dot_string

def generate_dump(policy, graph = None):

    if not graph:
        graph = generate_graph(policy)

    dump_string = "%d\n" % policy.num_fluents
    dump_string += "%d\n" % policy.id()

    dump_string += "%d\n" % graph.number_of_nodes()
    for node in graph.nodes():
        dump_string += "%d/%s\n" % (node.id(), node.label())

    edge_count = 0
    edge_dump = ""

    for (u,v) in graph.edges():
        if hash(u) != hash(v):

            is_high = graph.get_edge_data(u,v)['high']

            if 0 != is_high:
                edge_dump += "%d/%d/h\n" % (u.id(), v.id())
                edge_count += 1
            if 1 != is_high:
                edge_dump += "%d/%d/l\n" % (u.id(), v.id())
                edge_count += 1

    dump_string += "%d\n" % edge_count
    dump_string += edge_dump

    return dump_string

def generate_stats(policy, graph = None):

    if not graph:
        graph = generate_graph(policy)

    return (graph.number_of_nodes(), graph.number_of_edges())

def ITE(fg, h):
    global FALSE, LOOKUP_TABLE, NODE_LOOKUP

    if (fg.__class__ == InnerNode) and (h.__class__ == InnerNode):
        if not (fg.fluent == h.fluent):
            print fg.fluent
            print h.fluent
        assert fg.fluent == h.fluent

    # Base cases
    if fg.is_true():
        return fg

    if FALSE == fg:
        return h

    if FALSE == h:
        return fg

    if fg.id() == h.id():
        return h

    # Check hash on (fg, h)
    hash_val = "%d/%d" % (fg.id(), h.id())
    if hash_val in LOOKUP_TABLE:
        return LOOKUP_TABLE[hash_val]

    T = ITE(fg.high, h.high)
    E = ITE(fg.low, h.low)


    #####################################################################
    ## Attempt to hash the individual nodes to avoid re-creating them. ##
    #####################################################################

    new_node_key = "%s/%d/%d" % (str(fg.fluent), hash(T), hash(E))

    if new_node_key in NODE_LOOKUP:
        root = NODE_LOOKUP[new_node_key]
    else:
        root = InnerNode(fg.fluent)
        root.set_high(T)

        if T.id() == E.id():
            root.set_low(T)
        else:
            root.set_low(E)

        NODE_LOOKUP[new_node_key] = root

    #root = InnerNode(fg.fluent)
    #root.set_high(T)
    #
    #if T.id() == E.id():
    #    root.set_low(T)
    #else:
    #    root.set_low(E)

    # Insert (fg, h) -> root into the table
    LOOKUP_TABLE[hash_val] = root

    #print "fg: %s" % str(fg)
    #print "h: %s" % str(h)
    #print "T: %s" % str(T)
    #print "E: %s" % str(E)
    #print "ITE: %s\n" % str(root)

    return root

def generate_primitive_policy(prec_set, ordering):

    unseen = prec_set.prec

    if not unseen:
        return LeafNode(prec_set.candidate)

    prev_f = ordering[0]
    current = InnerNode(prev_f)
    root = current

    for f in ordering[1:]:

        if prev_f in unseen:
            saw_previous = True
            unseen.remove(prev_f)
        else:
            saw_previous = False

        if 0 == len(unseen):
            act_node = LeafNode(prec_set.candidate)
            current.set_high(act_node)
            current.set_low(FALSE)
            return root

        choice = InnerNode(f)
        current.set_high(choice)

        if saw_previous:
            current.set_low(FALSE)
        else:
            current.set_low(choice)

        current = choice
        prev_f = f

    if prev_f in unseen:
        unseen.remove(prev_f)

    if 0 == len(unseen):
        act_node = LeafNode(prec_set.candidate)
        current.set_high(act_node)
        current.set_low(FALSE)
        return root

    print "Error: Prec set wasn't used up by the ordering: %s / %s" % (str(prec_set), str(ordering))
    return None


def generate_variable_ordering(reg_list, mapping):
    seen = set()
    ordering = []
    for r in reg_list:
        for item in r:
            for ps in mapping[item]:
                new_vars = set(ps.prec) - seen
                ordering.extend(sorted(list(new_vars), cmp=lambda x,y: cmp(str(x), str(y))))
                seen |= new_vars

    return ordering

def generate_policy(reg_list, mapping):

    global LOOKUP_TABLE
    LOOKUP_TABLE = {}

    # Get the ordering
    ordering = generate_variable_ordering(reg_list, mapping)

    #print "Ordering:\n%s" % "\n".join([str(item) for item in ordering])
    import sys
    # Generate all of the primitive policies
    prim_policies = []
    for r in reg_list:
        for item in r:
            for ps in mapping[item]:
                prim_policies.append(generate_primitive_policy(ps, ordering))

    #for pp in prim_policies:
        #print pp
    #print "<<<"

    #global NODE_COUNT
    #print "Node count: %d" % NODE_COUNT

    # Iteratively create our large policy
    policy = prim_policies.pop(0)

    print "Iteratively building the ITE..."
    last = 0.0
    top_num = float(len(prim_policies))

    while prim_policies:
        #print str(sys.getsizeof(prim_policies[-1]))
        progress = (top_num - float(len(prim_policies))) / top_num
        if progress + 0.1 > last:
            last += 0.1
            print "%3.1f%% Complete" % (progress * 100)

        #print len(prim_policies)
        #print "Current: %s" % str(policy)

        policy = ITE(policy, prim_policies.pop(0))

    print "\nNodes used: %d\n" % NODE_COUNT

    policy.num_fluents = len(ordering)

    return policy
