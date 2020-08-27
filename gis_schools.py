import pulp
import pandas as pd
import os
import errno

def main():
    schulen = ['a', 'b', 'c'] #All schools
    lehren = [1, 2, 3] #All study directions
    gemeinden = ['Uster', 'Rüti', 'Zürich', 'Dummy'] #All places of living

    angebot = {'a': [1, 2], 'b': [2, 3], 'c': [1, 3]} #What school offers what study direction

    plaetze = {('a', 1): 10, ('a', 2): 6, ('a', 3): 0,
                ('b', 1): 0, ('b', 2): 10, ('b', 3): 10,
                ('c', 1): 10, ('c', 2): 0, ('c', 3): 10} #Number of available spaces

    lehrlinge = {('Uster', 1): 3, ('Uster', 2): 4, ('Uster', 3):1,
                ('Rüti', 1): 4, ('Rüti', 2): 2, ('Rüti', 3): 6,
                ('Zürich', 1): 3, ('Zürich', 2): 4, ('Zürich', 3): 3,
                ('Dummy', 1): 10, ('Dummy', 2): 6, ('Dummy', 3): 10} #Number of students per study direction for every commune

    zeit = {('Uster', 'a'): 3, ('Uster', 'b'): 5, ('Uster', 'c'): 4,
            ('Rüti', 'a'): 6, ('Rüti', 'b'): 1, ('Rüti','c'): 3,
            ('Zürich', 'a'): 2, ('Zürich', 'b'): 3, ('Zürich', 'c'): 6,
            ('Dummy', 'a'): 0, ('Dummy', 'b'): 0, ('Dummy', 'c'): 0} #Travel time between places of living and schools

    c = {}
    for g in gemeinden:
        for s in schulen:
            for a in angebot[s]:
                c[g, s, a] = zeit[g, s] #Theoretically redundant but not yet fixed

    zuteilung(gemeinden, schulen, lehren, c, lehrlinge, plaetze) #Calling assignment function

def zuteilung(gemeinden, schulen, lehren, c, lehrlinge, plaetze):
    '''
    Function to run the actual transportation problem
    
    :param gemeinden: List of all communes [type: List]
    :param schulen: List of all schools [type: List]
    :param lehren: List of all study directions [type: List]
    :param c: Dictionary of travel times between communes and schools (cost) [type: Dictionary]
    :param lehrlinge: Dictionary of students per commune and study direction [type: Dictionary]
    :param plaetze: Dictionary of spaces availabel per school and study direction [type: Dictionary]
    
    :return: None
    '''
    model = pulp.LpProblem(name='Schulen_Test', sense=pulp.LpMinimize) #Creating model
    
    x = {}
    for g,s,l in c: #Creating decision variables
        x[g,s,l] = pulp.LpVariable(name='x[{}, {}, {}]'.format(g,s,l), lowBound=0, cat=pulp.LpInteger) #Constraint (4) included
        
    a={}
    for g,s,l in x:
        if g != 'Dummy': #Dummy excluded since it is needed to balance the problem
            a[g,s,l] = pulp.LpVariable(name='assigned[{}, {}, {}]'.format(g,s,l), cat=pulp.LpBinary)
    
    #Constraint (2)
    for g in gemeinden:
        for l in lehren:
            model.addConstraint(pulp.LpConstraint(
                e=pulp.lpSum(x[g,s,l] for s in schulen if (g,s,l) in x),
                sense=pulp.LpConstraintEQ,
                name='Demand[{}, {}]'.format(g,l),
                rhs=lehrlinge[g,l]))
    
    #Constraint (3)
    for s in schulen:
        for l in lehren:
            model.addConstraint(pulp.LpConstraint(
                e=pulp.lpSum(x[g,s,l] for g in gemeinden if (g,s,l) in x),
                sense=pulp.LpConstraintLE,
                name='Capacity[{}, {}]'.format(s, l),
                rhs=plaetze[s, l]
            ))
    
    #Constraint(5)
    for g in gemeinden:
        if g != 'Dummy':
            for l in lehren:
                model.addConstraint(pulp.LpConstraint(
                    e=pulp.lpSum(a[g,s,l] for s in schulen if (g,s,l) in a),
                    sense=pulp.LpConstraintEQ,
                    name='Unique_assignment[{}, {}]'.format(g,l),
                    rhs=1
                ))

    M=10000

    for g in gemeinden:
        if g != 'Dummy':
            for l in lehren:
                for s in schulen:
                    if (g,s,l) in x:
                        model.addConstraint(pulp.LpConstraint(
                            e=x[g,s,l],
                            sense=pulp.LpConstraintGE,
                            name='Unique_lower_bound[{}, {}, {}]'.format(g,s,l),
                            rhs=lehrlinge[g,l] - M*(1-a[g,s,l])
                        ))

    for g in gemeinden:
        if g != 'Dummy':
            for l in lehren:
                for s in schulen:
                    if (g,s,l) in x:
                        model.addConstraint(pulp.LpConstraint(
                            e=x[g,s,l],
                            sense=pulp.LpConstraintLE,
                            name='Unique_upper_bound[{}, {}, {}]'.format(g,s,l),
                            rhs=M*a[g,s,l]
                        ))
    
    
    model.setObjective(pulp.lpSum(c[g,s,l] * x[g,s,l] for g,s,l in x)) #Objective function

    print('Writing lp file')
    model.writeLP(model.name + '.lp')

    print('Starting optimization')
    model.solve()
    print(pulp.LpStatus[model.status])

    #---------DEBUGGING------------#
    for g,s,l in x:
        if x[g,s,l].varValue != 0:
            print("{:10g} Schüler von {} aus Gemeinde {} an Schule {}".format(x[g,s,l].varValue, l, g, s)) #Print results for debugging purposes
    #------------------------------#
    
    #Export results to CSV
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
    '''
    Helper function to export data to  CSV
    
    :param output_df: Dataframe to be exported [type: pandas DataFrame]
    :param output_name: Name of output file [type: String]
    :param output_folder: Path of the output file [type: String]
    
    CREDIT: Ehsan Khodabandeh
    '''
    output_dir = get_file_directory(output_folder + '/')
    ensure_directory_exists(output_dir)
    out_name = ''.join((output_name, '.csv'))
    output_df.to_csv(os.path.join(output_dir, out_name), encoding='latin-1')

def ensure_directory_exists(directory):
    '''
    Creates directory if it doesn't exist yet. If it exists if does nothing unless the error is something else.
    
    :param directory: Directory to be created [type: String]
    
    CREDIT: Ehsan Khodabandeh
    '''
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def get_file_directory(file):
    '''
    Get directory of file
    
    :param file: File to be found [type: String]
    
    CREDIT: Ehsan Khodabandeh
    '''
    try:
        script_path = os.path.dirname(__file__)
    except NameError:
        return os.path.abspath(file)
    file_path = os.path.join(script_path, file)
    return file_path

if __name__ == '__main__':
    main()
