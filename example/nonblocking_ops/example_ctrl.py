"""The demonstration here does not require that the control client be
written using ocs.client_t (where the control script is a generator
and runs in the Twisted reactor).  But it's useful to have such
examples lying around.

"""

from ocs import client_t


def my_script(app, parser_args, target=None):
    print('Entered my_script')

    target_addr = '%s.%s' % (parser_args.address_root, target)

    # Obtain handles to both tasks.
    cw1 = client_t.TaskClient(app, target_addr, 'task1')
    cw2 = client_t.TaskClient(app, target_addr, 'task2')

    print('Starting first task.')
    d1 = yield cw1.start()
    print(d1)
    x = yield cw1.wait(timeout=20)
    print(x)

    print('Starting second task.')
    d2 = yield cw2.start()
    print(d2)
    x = yield cw2.wait(timeout=20)
    print(x)


if __name__ == '__main__':
    # We don't pass a parser in, so it will be auto-generated and
    # populated from the command line.  We hard-code our one argument,
    # the target agent instance_id.
    client_t.run_control_script2(my_script, target='example1')
