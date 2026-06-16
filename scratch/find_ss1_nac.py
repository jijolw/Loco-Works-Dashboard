import sys
sys.path.append('.')
from services.live_service import get_live_data
from services.decoders import decode_repair

res = get_live_data()
coaches = res.get('coaches', [])

print('Total live coaches:', len(coaches))

matching = []
for c in coaches:
    fam = (c.get('family') or '').upper()
    desc = (c.get('coach_desc') or '').upper()
    rep = (c.get('repair_type') or '').upper()
    
    if fam == 'LHB':
        st = 'LHB'
    else:
        continue
        
    if 'SS2' in rep or 'SS3' in rep or '121' in rep or '122' in rep or '241' in rep or '242' in rep or '243' in rep or '244' in rep:
        sched = 'SS2/SS3'
    else:
        sched = 'SS1'
        
    if desc.startswith(('LWSCN', 'LWS', 'LSCN', 'LS', 'LSLRD')):
        ac_nac = 'NAC'
    else:
        ac_nac = 'AC'
        
    cat = f'{st} {sched} {ac_nac}'
    if cat == 'LHB SS1 NAC':
        matching.append(c)

print('Found', len(matching), 'coaches matching LHB SS1 NAC:')
for c in matching:
    print(f"Coach: {c.get('coachno')}, Desc: {c.get('coach_desc')}, Repair: {c.get('repair_type')} ({decode_repair(c.get('repair_type'))}), Pit: {c.get('pitnum')}, Status: {c.get('status')}")
