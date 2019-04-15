import ocs
import time

agg = ocs.site_config.get_control_client('agg1')
faker = ocs.site_config.get_control_client('data1')

if 1:
    print('Aggregator -- initialize...')
    agg.request('start', 'initialize')
    print(agg.request('wait', 'initialize'))
    print(' - start aggregator.')
    agg.request('start', 'record')

if 1:
    print('Data Faker -- start 30 second acq.')
    faker.request('start', 'acq')
    for i in range(30):
        time.sleep(1)
        print(faker.request('status', 'acq'))
    faker.request('stop', 'acq')
    print(faker.request('wait', 'acq'))

if 1:
    print(' stop aggregator.')
    agg.request('stop', 'record')


