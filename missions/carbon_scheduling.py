"""Measured carbon scheduling scenario; catalog watts, actual workload days."""
from missions._common import load_csv, catalog_by_type, num
from finops.sustainability import REGION_CARBON, REGION_PRICE_KWH, carbon_g, energy_cost_usd


def run(verbose=True):
    cat = catalog_by_type()
    clean = min(REGION_CARBON, key=REGION_CARBON.get)
    cheap = min(REGION_PRICE_KWH, key=REGION_PRICE_KWH.get)
    jobs = []
    for j in load_csv('workloads.csv'):
        if not int(j['interruptible']):
            continue
        hours = num(j['hours_per_day']) * num(j['days']) * num(j['num_gpus'])
        wh = hours * num(cat[j['gpu_type']]['watts'])
        regions = {region: {'carbon_g': carbon_g(wh, region),
                           'electricity_usd': energy_cost_usd(wh, region)}
                   for region in REGION_CARBON}
        jobs.append({'job_id': j['job_id'], 'gpu_hours': hours, 'wh': wh, 'regions': regions})
    result = {'jobs': jobs, 'cleanest': clean, 'cheapest': cheap,
              'saved_g': sum(j['regions']['us-east-1']['carbon_g'] -
                             j['regions'][clean]['carbon_g'] for j in jobs)}
    if verbose:
        print(f"Carbon scheduling: {result['saved_g']:,.0f} gCO2e saved; cleanest={clean}, cheapest={cheap}")
    return result


if __name__ == '__main__':
    run()
