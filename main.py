import multiprocessing
import time
import fapar_instance

def parse_positions(inp):
    cds = []
    sides = ['N', 'W', 'E', 'S']

    p1 = 0
    for p2 in range(len(inp)):
        if inp[p2] in sides:
            degrees = int(inp[p1:p2]) // 10
            minutes = int((int(inp[p1:p2]) / 10 - degrees) * 60)
            cds.append(str(degrees) + '° ' + str(minutes) + '\' ' + inp[p2])
            p1 = p2 + 1

    print('1.\t' + cds[1] + '\t\t' + cds[2])
    print('2.\t' + cds[0] + '\t\t' + cds[2])
    print('3.\t' + cds[0] + '\t\t' + cds[3])
    print('4.\t' + cds[1] + '\t\t' + cds[3])
    print('\n\n')

def images_threading(number):
    pool = [None]*number
    PATH = 'C:\\Users\\kosiya\\Downloads\\Science\\Source_mean\\'

    for i in range(number):
        pool[i] = multiprocessing.Process(target=fapar_instance.image_thread, name=str(i + 1),
                                          args=(PATH + str(i + 1) + '\\',))
        pool[i].start()

    for i in range(number):
        pool[i].join()

def fapar_threading(instance, build_mode, thread_number=1):
    if not (1 < thread_number < 9):
        print('[THREAD] Launching for 1 thread')
        instance.build(build_mode)
    else:
        '''
        manager = multiprocessing.Manager()
        out = manager.dict()
        '''
        # adding Array of Manager is really kills multiprocess and increases time a lot (what`s the problem?)
        out = multiprocessing.Array('f', thread_number, lock=False)
        pool = [None] * thread_number

        for i in range(thread_number):
            pool[i] = multiprocessing.Process(target=instance.build, name=str(i + 1),
                                              args=(build_mode, i + 1, thread_number, out))
            pool[i].start()

        for p in pool:
            p.join()

        instance.set_mean(out)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Main~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if __name__ == '__main__':

    parse_positions('485N488N0449E0454E')

    LOCATION = 1
    MAP = {
        1: 'Moscow',
        2: 'Desert',
        3: 'Forest',
        4: 'Autumn_msk',
        5: 'Summer_msk'
    }

    print('[DEBUG] Passed ' + MAP[LOCATION] + ' location')

    # obj = fapar_instance.Fapar('C:\\Users\\kosiya\\Downloads\\Science\\Source\\' + MAP[LOCATION] + '\\')

    # launching multithreading
    print('[DEBUG] Building started. Current time ' + time.strftime("%H:%M:%S", time.localtime()))
    images_threading(2)
    # fapar_threading(obj, 'value', 1)
    print('[DEBUG] Building ended. Current time ' + time.strftime("%H:%M:%S", time.localtime()))

    # other operations
    # print('Mean fapar', obj.get_mean())
