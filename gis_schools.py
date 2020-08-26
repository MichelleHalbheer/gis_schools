import pulp
import pandas as pd
import os
import errno

def main():
    schulen = ['a', 'b', 'c']
    lehren = [1, 2, 3]
    gemeinden = ['Uster', 'Rüti', 'Zürich', 'Dummy']

    angebot = {'a': [1, 2], 'b': [2, 3], 'c': [1, 3]}

    plaetze = {('a', 1): 10, ('a', 2): 6, ('a', 3): 0,
                ('b', 1): 0, ('b', 2): 10, ('b', 3): 10,
                ('c', 1): 10, ('c', 2): 0, ('c', 3): 10}

    lehrlinge = {('Uster', 1): 3, ('Uster', 2): 4, ('Uster', 3):1,
                ('Rüti', 1): 4, ('Rüti', 2): 2, ('Rüti', 3): 6,
                ('Zürich', 1): 3, ('Zürich', 2): 4, ('Zürich', 3): 3,
                ('Dummy', 1): 10, ('Dummy', 2): 6, ('Dummy', 3): 10}

    zeit = {('Uster', 'a'): 3, ('Uster', 'b'): 5, ('Uster', 'c'): 4,
            ('Rüti', 'a'): 6, ('Rüti', 'b'): 1, ('Rüti','c'): 3,
            ('Zürich', 'a'): 2, ('Zürich', 'b'): 3, ('Zürich', 'c'): 6,
            ('Dummy', 'a'): 0, ('Dummy', 'b'): 0, ('Dummy', 'c'): 0}

    c = {}
    for g in gemeinden:
        for s in schulen:
            for a in angebot[s]:
                c[g, s, a] = zeit[g, s]

    zuteilung(gemeinden, schulen, lehren, c, lehrlinge, plaetze)

def zuteilung(gemeinden, schulen, lehren, c, lehrlinge, plaetze):
    model = pulp.LpProblem(name='Schulen_Test', sense=pulp.LpMinimize)
    
    x = {}
    for g,s,l in c:
        x[g,s,l] = pulp.LpVariable(name='x[{}, {}, {}]'.format(g,s,l), lowBound=0, cat=pulp.LpInteger)
    
    for g in gemeinden: #Lehrbetriebe
        for l in lehren: #Berufsgattungen
            model.addConstraint(pulp.LpConstraint(
                e=pulp.lpSum(x[g,s,l] for s in schulen if (g,s,l) in x),
                sense=pulp.LpConstraintEQ,
                name='Demand[{}, {}]'.format(g,l),
                rhs=lehrlinge[g,l]))
    
    for s in schulen: #Schulen
        for l in lehren:
            model.addConstraint(pulp.LpConstraint(
                e=pulp.lpSum(x[g,s,l] for g in gemeinden if (g,s,l) in x),
                sense=pulp.LpConstraintLE,
                name='Capacity[{}, {}]'.format(s, l),
                rhs=plaetze[s, l]
            ))
    
    for g in gemeinden:
        for l in lehren:
            model.addConstraint(pulp.LpConstraint(
                e=pulp.lpSum((x[g,s,l] - lehrlinge[g,l] if (x[g,s,l]==lehrlinge[g,l]) else x[g,s,l]) for s in schulen if (g,s,l) in x),
                sense=pulp.LpConstraintEQ,
                name='Unique_assignment[{}, {}]'.format(g,l),
                rhs=0
            ))
    
    
    model.setObjective(pulp.lpSum(c[g,s,l] * x[g,s,l] for g,s,l in x))

    print('Writing lp file')
    model.writeLP(model.name + '.lp')

    print('Starting optimization')
    model.solve()
    #print(model.constraints['Unique_assignments_Uster,_1_'])
    print(model.constraints)
    print(pulp.LpStatus[model.status])


    for g,s,l in x:
        if x[g,s,l].varValue != 0:
            print("{:10g} Schüler von {} aus Gemeinde {} an Schule {}".format(x[g,s,l].varValue, l, g, s))

    output = []
    for g,s,l in x:
        var_output = {
            'Gemeinde': g,
            'Schule': s,
            'Lehrgang': l,
            'Anzahl': x[g,s,l].varValue
        }
        output.append(var_output)
    output_df = pd.DataFrame.from_records(output).sort_values(['Lehrgang', 'Gemeinde'])
    output_df.set_index(['Lehrgang', 'Gemeinde'], inplace=True)
    write_to_csv(output_df=output_df)
    return

def write_to_csv(output_df, output_name='output', output_folder='output'):
    output_dir = get_file_directory(output_folder + '/')
    ensure_directory_exists(output_dir)
    out_name = ''.join((output_name, '.csv'))
    output_df.to_csv(os.path.join(output_dir, out_name), encoding='latin-1')

def ensure_directory_exists(directory):
    # Create the 'directory' if it doesn't exists. If it exists,
    # it does nothing unless the error code is something else!
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def get_file_directory(file):
    try:
        script_path = os.path.dirname(__file__)
    except NameError:
        return os.path.abspath(file)
    file_path = os.path.join(script_path, file)
    return file_path

if __name__ == '__main__':
    main()