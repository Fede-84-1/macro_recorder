import traceback, runpy, sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
try:
    runpy.run_module('app.main', run_name='__main__')
except Exception:
    traceback.print_exc()
    input("ERRORE. Premi Invio per chiudere.")
else:
    input("Programma terminato normalmente. Premi Invio per chiudere.")
