import ocs
import time

faker = ocs.site_config.get_control_client('data1')

print('Data Faker -- start 30 second acq.')
faker.request('start', 'acq')

for i in range(10):
    time.sleep(3)
    print(faker.request('status', 'acq'))

faker.request('stop', 'acq')
print(faker.request('wait', 'acq'))

