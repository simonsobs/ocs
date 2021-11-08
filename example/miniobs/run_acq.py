from ocs.ocs_client import OCSClient
import time

faker = OCSClient('data1')

print('Data Faker -- start 30 second acq.')
print(faker.acq.start())

print('\nMonitoring (ctrl-c to stop and exit)...\n')
try:
    for i in range(10):
        time.sleep(3)
        print(faker.acq.status())
except KeyboardInterrupt:
    print('Exiting on ctrl-c...')
    print()

print('Stop request...')
print(faker.acq.stop())
