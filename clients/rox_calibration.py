"""OCS Client for performing ROX calibration with two Lakeshore 372's.

Author: Brian Koopman
"""

import ocs
from ocs import client_t, site_config

def calibrate_roxes(app, pargs):

    print('Entered control')

    # Configure agent addresses, one for each of two LS372s
    control_agent_addr = f'{pargs.address_root}.control'
    measurement_agent_addr = f'{pargs.address_root}.measurement'

    # Task/Process registration
    control_init_task = client_t.TaskClient(app, control_agent_addr, 'init_lakeshore')
    measurement_init_task = client_t.TaskClient(app, measurement_agent_addr, 'init_lakeshore')

    # Measurement tasks
    set_measurement_ch_excitation_mode = client_t.TaskClient(app, measurement_agent_addr, 'set_excitation_mode')
    set_measurement_ch_excitation = client_t.TaskClient(app, measurement_agent_addr, 'set_excitation')

    # Control tasks
    set_heater_range = client_t.TaskClient(app, control_agent_addr, 'set_heater_range') 
    set_servo_ch_excitation_mode = client_t.TaskClient(app, control_agent_addr, 'set_excitation_mode')
    set_servo_ch_excitation = client_t.TaskClient(app, control_agent_addr, 'set_excitation')
    set_pid = client_t.TaskClient(app, control_agent_addr, 'set_pid')
    servo = client_t.TaskClient(app, control_agent_addr, 'servo_to_temperature')
    stability = client_t.TaskClient(app, control_agent_addr, 'check_temperature_stability')

    # Data acquisition processes
    control_acq_proc = client_t.ProcessClient(app, control_agent_addr, 'acq')
    measurement_acq_proc = client_t.ProcessClient(app, measurement_agent_addr, 'acq')
    
    print('Initializing control Lakeshore')
    d1 = yield control_init_task.start()
    
    print('Waiting for task to terminate...')
    x = yield control_init_task.wait(timeout=20)
    if x[0] == ocs.TIMEOUT:
        print('Timeout: the operation did not complete in a timely fashion!')
        return
    elif x[0] != ocs.OK:
        print('Error: the operation exited with error.')
        return
    else:
        print('The task has terminated.')
    
    print('Initializing measurement Lakeshore.')
    d1 = yield measurement_init_task.start()

    print('Waiting for task to terminate...')
    x = yield measurement_init_task.wait(timeout=20)
    if x[0] == ocs.TIMEOUT:
        print('Timeout: the operation did not complete in a timely fashion!')
        return
    elif x[0] != ocs.OK:
        print('Error: the operation exited with error.')
        return
    else:
        print('The task has terminated.')

    # Configure control and measurement channels
    servo_channel = 4
    calibrating_channels = [5]

    # Makes sure servo channel is in voltage excitation mode.
    yield set_servo_ch_excitation_mode.start(params={'channel': servo_channel, 'mode': 'voltage'})
    yield set_servo_ch_excitation_mode.wait()

    # Makes sure measurement channels are in voltage excitation mode.
    for channel in calibrating_channels:
        yield set_servo_ch_excitation_mode.start(params={'channel': channel, 'mode': 'voltage'})
        yield set_servo_ch_excitation_mode.wait()

    # Temperatures to calibrate to, based on provided Lakeshore calibration curves.
    temperatures = [0.8, 0.765, 0.73, 0.695, 0.66, 0.625, 0.595, 0.565, 0.535,
                    0.505, 0.482, 0.462, 0.442, 0.422, 0.404, 0.38, 0.36, 0.34, 0.32, 0.3, 0.28,
                    0.26, 0.24, 0.22, 0.2, 0.195, 0.19, 0.185, 0.18, 0.175, 0.17, 0.165, 0.16,
                    0.155, 0.15, 0.145, 0.14, 0.135, 0.13, 0.125, 0.12, 0.115, 0.11, 0.105, 0.1,
                    0.095, 0.09, 0.085, 0.08, 0.075, 0.07, 0.065, 0.06, 0.055, 0.05, 0.048, 0.047,
                    0.045, 0.044, 0.042, 0.04, 0.039, 0.038, 0.037, 0.036, 0.035, 0.034, 0.033,
                    0.032, 0.031, 0.03, 0.029, 0.028, 0.027, 0.026, 0.025, 0.024, 0.023, 0.022,
                    0.021, 0.020]

    # Start at low temperature.
    temperatures.reverse()

    # Calibration loop
    for t in temperatures:
        if t == 0.020:
            excitation = 20e-6
            pid = {"P": 160, "I": 10, "D": 0}
            print(f"Changing PID parameters to {pid['P']}, {pid['I']}, {pid['D']}")
            yield set_pid.start(params=pid)
            yield set_pid.wait()

        if t == 0.040:
            pid = {"P": 40, "I": 2, "D": 0}
            print(f"Changing PID parameters to {pid['P']}, {pid['I']}, {pid['D']}")
            yield set_pid.start(params=pid)
            yield set_pid.wait()

        if t == 0.050:
            excitation = 63.2e-6

        if t == 0.060:
            excitation = 200e-6

        if t == 0.250:
            excitation = 632e-6

        if t == 0.300:
            excitation = 200e-6

        if t >= 0.505:
            excitation = 2.0e-3

        print(f"Changing servo channel excitation voltage to {excitation}")
        yield set_servo_ch_excitation.start(params={'channel': servo_channel, 'value': excitation})
        yield set_servo_ch_excitation.wait()

        for channel in calibrating_channels:
            print(f"Changing measurement channel {channel}'s excitation voltage to {excitation}")
            yield set_measurement_ch_excitation.start(params={'channel': channel, 'value': excitation})
            yield set_measurement_ch_excitation.wait()

        print('Adjusting heater...')
        if t >= 0.020 and t <= 0.05:
            _range = 1e-3
        elif t > 0.05 and t <= 0.25:
            _range = 3.16e-3
        elif t > 0.25:
            _range = 10e-3

        yield set_heater_range.start(params={'range': _range, 'wait': 1})
        yield set_heater_range.wait()
        print(f"Set heater range to {_range}")

        print(f"Setting servo setpoint to {t} K")
        s1 = yield servo.start(params={'temperature': t})
        s2 = yield servo.wait()

        # Wait a bit for temperature to start moving - normally ~180 seconds
        print("Sleeping 1 second for the setpoint change demo")
        yield client_t.dsleep(1)

        move_on = False
        while move_on is False:
            d1 = yield stability.start(params={'measurements': 20, 'threshold': 0.5e-3, 'attempts': 1, 'pause': 10})
            d2 = yield stability.wait()

            if d1[2]['success']:
                move_on = True
            else:
                print("Temperatures still not stable, waiting.")
                # yield client_t.dsleep(10)

        print('Starting a data acquisition process...')
        d1 = yield control_acq_proc.start()
        d1 = yield measurement_acq_proc.start()

        sleep_time = 30
        try:
            for i in range(sleep_time):
                print('sleeping for {:d} more seconds'.format(sleep_time - i))
                yield client_t.dsleep(1)
        finally:
            print("Stopping acquisition process")
            yield control_acq_proc.stop()
            yield control_acq_proc.wait()
            yield measurement_acq_proc.stop()
            yield measurement_acq_proc.wait()

if __name__ == '__main__':
    parser = site_config.add_arguments()
    client_t.run_control_script2(calibrate_roxes, parser=parser)
