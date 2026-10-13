"""Additional extension checks; original tests/ stays untouched."""
import csv
import json
import math
from pathlib import Path
from finops import pricing
from missions._common import load_csv
from missions.m2_inference_levers import optimized_request_cost, run
from missions.carbon_scheduling import run as carbon_run


def main():
    threshold = pricing.cache_break_even_reads(3, 3.75)
    assert math.isclose(threshold, 1.25 / .9)
    assert not pricing.cache_is_worth_it(threshold, 3.75, 3)
    assert not pricing.cache_is_worth_it(1, 3.75, 3)
    assert pricing.cache_is_worth_it(5, 3.75, 3)
    sample = dict(input_tokens='1000', output_tokens='100', cached_input_tokens='1000',
                  route_tier='large', is_batch='1')
    full = pricing.request_cost(1000, 100, 3, 15, batch=True)
    assert optimized_request_cost(sample, 2) == full  # batch gate rejects two reads
    assert optimized_request_cost(sample, 5) < full
    assert optimized_request_cost(sample, 0) == full
    for args in [(-1, 3.75, 3), (1, -1, 3), (1, 1, 0)]:
        try:
            pricing.cache_is_worth_it(*args)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid cache input accepted')
    r = run(False)
    assert math.isclose(r['stages']['with_write'], r['cache_scenarios'][1]['cost'])
    costs = sum(optimized_request_cost(row) for row in load_csv('token_usage.csv'))
    assert math.isclose(costs, r['stages']['with_write'])
    with Path('outputs/focus_export.csv').open(newline='') as f:
        exported = list(csv.DictReader(f))
    assert len(exported) == 50
    for fr, row in zip(exported, load_csv('token_usage.csv')[:50]):
        assert abs(float(fr['BilledCost']) - optimized_request_cost(row)) <= .000051
    c = carbon_run(False)
    workloads = {j['job_id']: j for j in load_csv('workloads.csv')}
    for j in c['jobs']:
        w = workloads[j['job_id']]
        assert int(w['interruptible']) == 1
        assert j['gpu_hours'] == float(w['days']) * float(w['hours_per_day']) * float(w['num_gpus'])
    assert math.isclose(c['saved_g'], 626150)
    Path('outputs/after.json').write_text(json.dumps({'M2':r, 'carbon':c},indent=2),encoding='utf-8')
    print('Extension checks passed: cache boundary/batch/invalid inputs, FOCUS consistency, carbon workload invariance.')


if __name__ == '__main__':
    main()
