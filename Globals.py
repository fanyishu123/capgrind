
D = 4
RL_DIM = {0 : 5.5, 1 : 1.1, 2 : 1.1, 3 : 0}
AXES = { 0 : 'Z', 1 : 'Y', 2 : 'X', 3 : 'B'}
CMAPS = {'Greyscale' : 'gray', 'Jet' : 'jet', 'Blue monotone' : 'Blues_r'}
NORM_3D = dict([(tuple({0,1,2} - {i}),i) for i in range(3)])

# Some syntatic sugar: @trigger_update f makes python run self.update() after self.f()
def trigger_update(function):
    def run_function(self, *args, **kwargs):
        ret = function(self, *args, **kwargs)
        self.updated()
        return ret
    return run_function

# 'cause I'm a voodoo child
def trigger_update_args(*updatepos):
    def func_update(function):
        def run_function(self, *args, **kwargs):
            ret = function(self, *args, **kwargs)
            self.updated((args[pos] for pos in updatepos))
            return ret
        return run_function
    return func_update