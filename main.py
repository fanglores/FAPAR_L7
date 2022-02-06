import multiprocessing
import time
import fapar_instance

if __name__ == '__main__':

    def fapar_threading(instance, build_mode, thread_number=1):
        #print(len(obj.img_fapar))
        #parse output data as length

        if not (1 < thread_number < 9):
            print('[THREAD] Launching for 1 thread')
            instance.build(build_mode)
        else:
            #manager = multiprocessing.Manager()
            #out = manager.dict()
            out = multiprocessing.Array('f', thread_number)
            pool = [None] * thread_number

            for i in range(thread_number):
                pool[i] = multiprocessing.Process(target=instance.build, name=str(i + 1),
                                                  args=(build_mode, i + 1, thread_number, out, i))
                pool[i].start()

            for p in pool:
                p.join()

        instance.set_mean(out)
        print(instance.get_mean())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Main~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    DEBUG_MODE = False

    LOCATION = 1
    MAP = {
        1: 'Moscow',
        2: 'Desert',
        3: 'Forest',
        4: 'Autumn_msk',
        5: 'Summer_msk'
    }

    print('[DEBUG] Passed ' + MAP[LOCATION] + ' location')

    obj = fapar_instance.Fapar('C:\\Users\\kosiya\\Downloads\\Science\\Source\\' + MAP[LOCATION] + '\\')

    # launching multithreading
    print('[DEBUG] Building started. Current time ' + time.strftime("%H:%M:%S", time.localtime()))
    fapar_threading(obj, 'value', 2)
    print('[DEBUG] Building ended. Current time ' + time.strftime("%H:%M:%S", time.localtime()))

    # other operations
    print('Mean fapar', obj.get_mean())
