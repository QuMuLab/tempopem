
# Depots
depots = []
for i in range(1,23):
    depots.append(('domains/depots/domain.pddl', "domains/depots/pfile%d" % i))

# Driverlog
driverlog = []
for i in range(1,21):
    driverlog.append(('domains/driverlog/domain.pddl', "domains/driverlog/pfile%d" % i))

# Logistics
logistics = []
for i in range(1,10):
    logistics.append(('domains/logistics/domain.pddl', "domains/logistics/prob0%d.pddl" % i))
for i in range(10, 36):
    logistics.append(('domains/logistics/domain.pddl', "domains/logistics/prob%d.pddl" % i))

# Openstacks -- Note: problems above p07 are too large for FF
openstacks = []
for i in range(1,8):
#for i in range(1,10):
    openstacks.append(("domains/openstacks/domain_p0%d.pddl" % i, "domains/openstacks/p0%d.pddl" % i))
#for i in range(10, 31):
#    openstacks.append(("domains/openstacks/domain_p%d.pddl" % i, "domains/openstacks/p%d.pddl" % i))

# Rovers
rovers = []
for i in range(1,21):
    rovers.append(('domains/rovers/domain.pddl', "domains/rovers/pfile%d" % i))

# Storage
storage = []
for i in range(1,10):
    storage.append(('domains/storage/domain.pddl', "domains/storage/p0%d.pddl" % i))
for i in range(10, 31):
    storage.append(('domains/storage/domain.pddl', "domains/storage/p%d.pddl" % i))

# TPP
tpp = []
for i in range(1,10):
    tpp.append(("domains/tpp/domain_p0%d.pddl" % i, "domains/tpp/p0%d.pddl" % i))
for i in range(10, 31):
    tpp.append(("domains/tpp/domain_p%d.pddl" % i, "domains/tpp/p%d.pddl" % i))

# Trucks
trucks = []
for i in range(1,10):
    trucks.append(("domains/trucks/domain_p0%d.pddl" % i, "domains/trucks/p0%d.pddl" % i))
for i in range(10, 31):
    trucks.append(("domains/trucks/domain_p%d.pddl" % i, "domains/trucks/p%d.pddl" % i))

# Zenotravel
zenotravel = []
for i in range(1,21):
    zenotravel.append(('domains/zenotravel/domain.pddl', "domains/zenotravel/pfile%d" % i))

# Manufactured dependent
dependent = []
for i in range(2,9):
    dependent.append(("domains/manufactured/dependent/domain%d.pddl" % i, "domains/manufactured/dependent/prob%d.pddl" % i))

# Manufactured dependent2
dependent2 = []
for i in range(2,11):
    dependent2.append(("domains/manufactured/dependent2/domain%d.pddl" % i, "domains/manufactured/dependent2/prob%d.pddl" % i))

# Manufactured pairs
pairs = []
for i in range(2,11):
    pairs.append(("domains/manufactured/pairs/domain%d.pddl" % i, "domains/manufactured/pairs/prob%d.pddl" % i))

# Manufactured parallel
parallel = []
for i in range(2,11):
    parallel.append(("domains/manufactured/parallel/domain%d.pddl" % i, "domains/manufactured/parallel/prob%d.pddl" % i))

# Manufactured tail
tail = []
for i in range(1,9):
    tail.append(("domains/manufactured/tail/domain%d0.pddl" % i, "domains/manufactured/tail/prob%d0.pddl" % i))

# FINAL
DOMAINS = {
    'depots': depots,
    'driverlog': driverlog,
    'logistics': logistics,
    'openstacks': openstacks,
    'rovers': rovers,
    'storage': storage,
    'tpp': tpp,
    'trucks': trucks,
    'zenotravel': zenotravel,
    'dependent': dependent,
    'dependent2': dependent2,
    'parallel': parallel,
    'tail': tail,
    'pairs': pairs
}

GOOD_DOMAINS = ['depots', 'driverlog', 'tpp', 'zenotravel', 'rovers']
