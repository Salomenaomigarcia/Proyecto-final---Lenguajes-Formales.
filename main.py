"""Proyecto de Lenguajes Formales - Dragon Book (4.4, 4.6, 5.1-5.2).

VERSION SENCILLA: un solo archivo, solo libreria estandar de Python.

Como se guarda la gramatica:
    Un diccionario: cabeza -> lista de cuerpos (texto).
    Ejemplo:  S -> aA b    se guarda como   {'S': ['aA', 'b']}
    Epsilon (la cadena vacia) se guarda como '' (texto vacio).
    Cada simbolo es UN solo caracter. Mayuscula = no terminal.

Como correrlo:
    python3 main_sencillo.py                 -> parsers LL(1) / SLR(1)
    python3 main_sencillo.py --sets          -> ademas imprime FIRST y FOLLOW
    python3 main_sencillo.py --table         -> imprime tablas
    python3 main_sencillo.py --trace         -> muestra cada paso del parser
    python3 main_sencillo.py --sdd [--graph] -> Item 3 (evaluador SDD)
    python3 main_sencillo.py --cycle-demo    -> demuestra deteccion de ciclos
    python3 main_sencillo.py --demo          -> ejemplos sin escribir nada
    python3 main_sencillo.py --test          -> pruebas automaticas
    python3 main_sencillo.py --info          -> version de SO y de Python
"""

import sys
import platform

# SIMBOLOS ESPECIALES
EPS = 'e'      # epsilon (cadena vacia). NO es un terminal real.
END = '$'      # marca el final de la palabra
START = "S'"   # simbolo inicial nuevo (para aumentar la gramatica en SLR)


# ======================================================================
# 1. LEER LA GRAMATICA, FIRST Y FOLLOW  (Dragon Book 4.4.2)
# ======================================================================

# Terminal = cualquier simbolo del cuerpo que NO es cabeza de una regla.
def terminals_of(grammar):
    terminals = set()
    for head in grammar:
        for rhs in grammar[head]:
            for symbol in rhs:
                if symbol not in grammar:
                    terminals.add(symbol)
    return terminals


# Lee:  n  y despues n lineas como   S -> aA b
def read_grammar():
    grammar = {}
    n = int(input().strip())
    for _ in range(n):
        line = input()
        head, body = line.split('->')
        alternatives = []
        for alt in body.split():
            if alt == EPS:
                alternatives.append('')      # epsilon = texto vacio
            else:
                alternatives.append(alt)
        grammar[head.strip()] = alternatives
    if 'S' not in grammar:
        raise ValueError('The grammar must have a start symbol S.')
    return grammar


# FIRST de una SECUENCIA de simbolos.
# Idea: "con que letras puede EMPEZAR lo que sale de esta secuencia?"
# Recorremos de izquierda a derecha; si un simbolo puede desaparecer (e),
# miramos tambien el siguiente. Si TODOS pueden desaparecer, agregamos e.
def first_of_string(symbols, first):
    result = set()
    for symbol in symbols:
        for x in first[symbol]:
            if x != EPS:
                result.add(x)
        if EPS not in first[symbol]:
            return result            # este simbolo NO desaparece: paramos
    result.add(EPS)                  # todos desaparecen (o no habia nada)
    return result


# FIRST de cada simbolo, por "punto fijo":
# repetimos hasta que ningun conjunto crezca mas.
def first_sets(grammar, terminals):
    first = {}
    for t in terminals:
        first[t] = {t}               # FIRST(terminal) = el mismo terminal
    for nt in grammar:
        first[nt] = set()            # los no terminales empiezan vacios
    changed = True
    while changed:
        changed = False
        for head in grammar:
            for rhs in grammar[head]:
                for x in first_of_string(rhs, first):
                    if x not in first[head]:
                        first[head].add(x)
                        changed = True
    return first


# FOLLOW(A) = terminales que pueden aparecer justo DESPUES de A.
# Reglas:
#   1) $ esta en FOLLOW(S).
#   2) En  X -> alfa A beta : FIRST(beta) (sin e) entra a FOLLOW(A).
#   3) Si beta puede desaparecer: FOLLOW(X) entra a FOLLOW(A).
def follow_sets(grammar, first):
    follow = {}
    for nt in grammar:
        follow[nt] = set()
    follow['S'].add(END)
    changed = True
    while changed:
        changed = False
        for head in grammar:
            for rhs in grammar[head]:
                for i in range(len(rhs)):
                    nt = rhs[i]
                    if nt not in grammar:
                        continue                      # solo no terminales
                    after = first_of_string(rhs[i + 1:], first)
                    to_add = []
                    for x in after:
                        if x != EPS:
                            to_add.append(x)
                    if EPS in after:
                        to_add = to_add + list(follow[head])
                    for x in to_add:
                        if x not in follow[nt]:
                            follow[nt].add(x)
                            changed = True
    return follow


# Formato pedido: terminales en orden ASCII, luego e, luego $.
def set_text(values):
    letters = []
    for x in values:
        if x != EPS and x != END:
            letters.append(x)
    letters.sort()
    if EPS in values:
        letters.append(EPS)
    if END in values:
        letters.append(END)
    return '{' + ', '.join(letters) + '}'


# Para mostrar una produccion:  ('A', '') -> 'A -> e'
def rule_text(head, rhs):
    if rhs == '':
        return head + ' -> ' + EPS
    return head + ' -> ' + rhs


# ======================================================================
# 2. PARSER LL(1): TABLA + PILA  (Dragon Book 4.4.3 y 4.4.4)
# ======================================================================

# Tabla M[A, a]: para cada regla A -> alfa la ponemos en las columnas
# FIRST(alfa) (sin e); si alfa puede ser vacia, tambien en FOLLOW(A).
# Si una casilla recibe dos reglas DIFERENTES -> NO es LL(1).
def make_ll_table(grammar, first, follow):
    table = {}
    valid = True
    for head in grammar:
        for rhs in grammar[head]:
            lookaheads = first_of_string(rhs, first)
            columns = []
            for x in lookaheads:
                if x != EPS:
                    columns.append(x)
            if EPS in lookaheads:
                columns = columns + list(follow[head])
            for symbol in columns:
                key = (head, symbol)
                if key in table and table[key] != rhs:
                    valid = False            # conflicto
                else:
                    table[key] = rhs
    return table, valid


# Un nodo del arbol sintactico. Sirve para LL y para SLR.
class Node:
    def __init__(self, symbol, grammar):
        self.symbol = symbol
        self.production = None     # (cabeza, cuerpo) si es no terminal
        self.children = []
        self.number = 0            # numero para imprimir (S1, A2, ...)
        if symbol in grammar:
            self.attrs = {}                    # no terminal: se calculan luego
        else:
            self.attrs = {'lexval': symbol}    # terminal: lexval = su caracter


# Parser LL(1) no recursivo con una PILA (como una pila de platos:
# siempre sacamos el de ARRIBA). Empieza con [ $, S ].
#   - tope es terminal    -> debe coincidir con la entrada
#   - tope es no terminal -> miramos la tabla M[tope, siguiente caracter]
# Devuelve la raiz del arbol si acepta, o None si rechaza.
def parse_ll(word, grammar, table, trace=False):
    root = Node('S', grammar)
    stack = [(END, None), ('S', root)]
    pos = 0
    while len(stack) > 0:
        symbol, node = stack.pop()
        if pos < len(word):
            lookahead = word[pos]
        else:
            lookahead = END

        if symbol == END:
            # Aceptamos solo si ya consumimos TODA la palabra
            if trace:
                print('LL: end marker ->', 'accept' if pos == len(word) else 'reject')
            if pos == len(word):
                return root
            return None

        if symbol not in grammar:                  # es terminal
            if trace:
                print('LL: match', symbol, '| input:', word[pos:] + END)
            if symbol != lookahead:
                return None
            pos += 1
            continue

        rhs = table.get((symbol, lookahead))       # es no terminal
        if rhs is None:
            if trace:
                print('LL: no table entry for', (symbol, lookahead))
            return None
        if trace:
            print('LL:', rule_text(symbol, rhs), '| input:', word[pos:] + END)

        node.production = (symbol, rhs)
        for x in rhs:
            node.children.append(Node(x, grammar))
        # Apilamos de DERECHA a IZQUIERDA para que el primer simbolo
        # del cuerpo quede arriba y se procese primero.
        i = len(rhs) - 1
        while i >= 0:
            stack.append((rhs[i], node.children[i]))
            i -= 1
    return None


# ======================================================================
# 3. PARSER SLR(1)  (Dragon Book 4.6.2, 4.6.3 y 4.6.4)
# ======================================================================
# Un ITEM es (numero_de_produccion, posicion_del_punto).
# Ejemplo:  A -> a . B   = "ya vi a, ahora espero B".
# Un ESTADO es una lista ordenada de items.

# CLOSURE: si el punto esta antes de un no terminal B, agregamos todos
# los items  B -> . gamma.  Repetimos hasta que no aparezca nada nuevo.
def closure(items, productions, grammar):
    result = list(items)
    changed = True
    while changed:
        changed = False
        for p, dot in list(result):
            rhs = productions[p][1]
            if dot < len(rhs) and rhs[dot] in grammar:
                for j in range(len(productions)):
                    if productions[j][0] == rhs[dot] and (j, 0) not in result:
                        result.append((j, 0))
                        changed = True
    result.sort()
    return result


# GOTO(I, X): movemos el punto a la derecha de X y aplicamos CLOSURE.
def goto_items(items, symbol, productions, grammar):
    moved = []
    for p, dot in items:
        rhs = productions[p][1]
        if dot < len(rhs) and rhs[dot] == symbol:
            moved.append((p, dot + 1))
    return closure(moved, productions, grammar)


# Coleccion canonica de estados LR(0). Aumentamos: S' -> S (produccion 0).
# Devuelve (producciones, estados, transiciones).
def lr0_automaton(grammar):
    productions = [(START, 'S')]
    for head in grammar:
        for rhs in grammar[head]:
            productions.append((head, rhs))

    states = [closure([(0, 0)], productions, grammar)]
    edges = {}                     # (estado, simbolo) -> estado destino
    i = 0
    while i < len(states):         # states crece mientras recorremos
        items = states[i]
        symbols = []               # simbolos que estan justo despues del punto
        for p, dot in items:
            rhs = productions[p][1]
            if dot < len(rhs) and rhs[dot] not in symbols:
                symbols.append(rhs[dot])
        symbols.sort()
        for symbol in symbols:
            target = goto_items(items, symbol, productions, grammar)
            if target in states:
                j = states.index(target)    # estado ya existente
            else:
                states.append(target)       # estado nuevo
                j = len(states) - 1
            edges[(i, symbol)] = j
        i += 1
    return productions, states, edges


# Pone una accion en la tabla. Devuelve True si hay CONFLICTO.
def add_action(action, key, value):
    if key in action and action[key] != value:
        return True
    action[key] = value
    return False


# Tablas ACTION y GOTO.
#   shift  : transicion con terminal
#   goto   : transicion con no terminal
#   reduce : item completo A -> alfa .  en cada terminal de FOLLOW(A)
#   accept : item  S' -> S .  con $
# Si hay conflicto (shift/reduce o reduce/reduce) NO es SLR(1).
def make_slr_table(grammar, follow):
    productions, states, edges = lr0_automaton(grammar)
    action = {}
    goto = {}
    valid = True
    for (state, symbol), target in edges.items():
        if symbol in grammar:
            goto[(state, symbol)] = target
        else:
            if add_action(action, (state, symbol), ('shift', target)):
                valid = False
    for state in range(len(states)):
        for p, dot in states[state]:
            head, rhs = productions[p]
            if dot == len(rhs):                      # item completo
                if p == 0:
                    if add_action(action, (state, END), ('accept',)):
                        valid = False
                else:
                    for symbol in follow[head]:
                        if add_action(action, (state, symbol), ('reduce', p)):
                            valid = False
    return action, goto, productions, states, edges, valid


# Parser SLR(1) (shift-reduce) con pila de estados.
#   shift  : leer un caracter y apilar el nuevo estado
#   reduce : cambiar el cuerpo de una regla por su cabeza (arma el arbol)
#   accept : terminamos bien
#   sin accion : error -> None
def parse_slr(word, grammar, action, goto, productions, trace=False):
    states = [0]       # pila de estados
    nodes = []         # pila de nodos (el arbol se arma de abajo hacia arriba)
    pos = 0
    while True:
        if pos < len(word):
            lookahead = word[pos]
        else:
            lookahead = END
        operation = action.get((states[-1], lookahead))
        if trace:
            if operation is None:
                shown = 'error'
            else:
                shown = operation
            print('SLR: states', states, '| input:', word[pos:] + END,
                  '| action:', shown)
        if operation is None:
            return None

        if operation[0] == 'shift':
            nodes.append(Node(lookahead, grammar))
            states.append(operation[1])
            pos += 1

        elif operation[0] == 'reduce':
            head, rhs = productions[operation[1]]
            count = len(rhs)
            children = []
            if count > 0:
                children = nodes[-count:]
                del nodes[-count:]
                del states[-count:]
            target = goto.get((states[-1], head))
            if target is None:
                return None
            new_node = Node(head, grammar)
            new_node.production = (head, rhs)
            new_node.children = children
            nodes.append(new_node)
            states.append(target)

        else:   # accept
            if pos == len(word) and len(nodes) == 1:
                return nodes[0]
            return None


# Imprime tabla LL, estados LR(0), transiciones, ACTION y GOTO (--table).
def print_tables(ll, action, goto, productions, states, edges):
    print('LL(1) table:')
    for (head, t), rhs in sorted(ll.items()):
        print('  M[{}, {}] = {}'.format(head, t, rule_text(head, rhs)))
    print('LR(0) states:')
    for i in range(len(states)):
        print('  State', i)
        for p, dot in states[i]:
            head, rhs = productions[p]
            print('   ', head, '->', rhs[:dot] + '.' + rhs[dot:])
    print('LR(0) transitions:')
    for (i, symbol), target in sorted(edges.items()):
        print('  goto({}, {}) = {}'.format(i, symbol, target))
    print('SLR ACTION entries:')
    for (i, symbol), value in sorted(action.items()):
        print('  ACTION[{}, {}] = {}'.format(i, symbol, value))
    print('SLR GOTO entries:')
    for (i, symbol), value in sorted(goto.items()):
        print('  GOTO[{}, {}] = {}'.format(i, symbol, value))


# ======================================================================
# 4. ITEM 3: SDD  (Dragon Book 5.1 y 5.2)
# ======================================================================
# GRAMATICA PROPIA:
#     S -> A
#     A -> aA | bB
#     B -> cB | dC
#     C -> fC | g
# Lenguaje:  a* b c* d f* g     Ejemplos: bdg, abdg, abccdg
# 4 no terminales, 7 producciones, A, B y C son recursivas. Es LL(1).
#
# ATRIBUTOS:
#   A.level  HEREDADO    cuantas 'a' hay antes de este A
#   X.score  SINTETIZADO puntaje del subarbol
# RESULTADO:  S.score = (largo de la palabra) + (numero de 'a' iniciales)
# Ejemplo abccdg: largo 6 + una 'a' = 7.
#
# CLASIFICACION: es L-atribuida. El unico atributo heredado (A.level) se
# calcula SOLO con el atributo heredado del padre (A1.level = A.level + 1)
# o con una constante (A.level = 0, regla de S). NO es S-atribuida porque
# tiene un atributo heredado.
SDD_GRAMMAR = {
    'S': ['A'],
    'A': ['aA', 'bB'],
    'B': ['cB', 'dC'],
    'C': ['fC', 'g'],
}
SDD_MAIN = 'score'


# Una regla semantica es un DATO con tres partes:
#   target   : atributo que define, como (posicion, nombre)
#              posicion -1 = la cabeza; 0, 1, ... = hijos del cuerpo
#   uses     : lista de atributos que necesita, mismo formato
#   function : funcion que recibe la lista de valores y devuelve el nuevo
class Rule:
    def __init__(self, target, uses, function):
        self.target = target
        self.uses = uses
        self.function = function


# Funciones de calculo (simples, una operacion cada una).
# 'v' es la lista de valores de los atributos que la regla usa.
def value_zero(v):
    return 0

def value_one(v):
    return 1

def copy_first(v):
    return v[0]

def add_one(v):
    return 1 + v[0]

def add_one_and_level(v):
    return 1 + v[0] + v[1]


# Reglas por produccion (la llave es (cabeza, cuerpo)):
#   S -> A    : A.level = 0 ; S.score = A.score
#   A -> aA1  : A1.level = A.level + 1 ; A.score = 1 + A1.score
#   A -> bB   : A.score = 1 + A.level + B.score
#   B -> cB1  : B.score = 1 + B1.score
#   B -> dC   : B.score = 1 + C.score
#   C -> fC1  : C.score = 1 + C1.score
#   C -> g    : C.score = 1
SDD_RULES = {
    ('S', 'A'): [
        Rule((0, 'level'), [], value_zero),
        Rule((-1, 'score'), [(0, 'score')], copy_first),
    ],
    ('A', 'aA'): [
        Rule((1, 'level'), [(-1, 'level')], add_one),
        Rule((-1, 'score'), [(1, 'score')], add_one),
    ],
    ('A', 'bB'): [
        Rule((-1, 'score'), [(-1, 'level'), (1, 'score')], add_one_and_level),
    ],
    ('B', 'cB'): [Rule((-1, 'score'), [(1, 'score')], add_one)],
    ('B', 'dC'): [Rule((-1, 'score'), [(1, 'score')], add_one)],
    ('C', 'fC'): [Rule((-1, 'score'), [(1, 'score')], add_one)],
    ('C', 'g'):  [Rule((-1, 'score'), [], value_one)],
}


# Lista los nodos en preorden (raiz primero) y les pone numero.
# Usamos una pila y NO recursion para que un arbol muy profundo
# no rompa el limite de recursion de Python.
def tree_nodes(root):
    result = []
    pending = [root]
    while len(pending) > 0:
        node = pending.pop()
        result.append(node)
        node.number = len(result)
        i = len(node.children) - 1
        while i >= 0:
            pending.append(node.children[i])
            i -= 1
    return result


# Convierte una referencia local como (1, 'score') en
# (nodo real del arbol, 'score').
def resolve(node, ref):
    position, attr = ref
    if position == -1:
        return (node, attr)
    return (node.children[position], attr)


# Nombre legible de un atributo:  A2.level, S1.score, a3.lexval
def attribute_name(key):
    node, attr = key
    return '{}{}.{}'.format(node.symbol, node.number, attr)


# EVALUADOR GENERAL. No sabe nada de esta SDD: solo lee 'rules'.
# Pasos:
#   1) instanciar las reglas en cada nodo del arbol
#   2) armar el grafo de dependencias (vertice = (nodo, atributo))
#      arista  A -> B  significa "B necesita a A"
#   3) orden topologico (algoritmo de Kahn)
#   4) calcular cada atributo en ese orden
# Si sobran vertices sin visitar, hay un CICLO -> SDD circular.
# Devuelve (orden, valor_del_atributo_principal, aristas).
def evaluate_sdd(root, rules=SDD_RULES, main_attribute=SDD_MAIN):
    nodes = tree_nodes(root)

    # Paso 1: tareas pendientes  (nodo, atributo) -> (funcion, dependencias)
    tasks = {}
    for node in nodes:
        if node.production is None:
            continue                      # los terminales no tienen reglas
        if node.production not in rules:
            raise ValueError('Missing semantic rules: ' + str(node.production))
        for rule in rules[node.production]:
            key = resolve(node, rule.target)
            if key in tasks or key[1] in key[0].attrs:
                raise ValueError('Attribute defined more than once: '
                                 + attribute_name(key))
            deps = []
            for ref in rule.uses:
                deps.append(resolve(node, ref))
            tasks[key] = (rule.function, deps)

    # Paso 2: vertices y aristas. Los lexval de los terminales ya son
    # conocidos, pero tambien son vertices del grafo.
    vertices = []
    for node in nodes:
        for attr in node.attrs:
            vertices.append((node, attr))
    for key in tasks:
        vertices.append(key)

    indegree = {}     # cuantas dependencias le faltan a cada vertice
    following = {}    # quienes dependen de cada vertice
    for v in vertices:
        indegree[v] = 0
        following[v] = []

    edges = []
    for target in tasks:
        deps = tasks[target][1]
        unique = []
        for dep in deps:
            if dep not in unique:
                unique.append(dep)
        for dep in unique:
            if dep not in indegree:
                raise ValueError('Undefined attribute: ' + attribute_name(dep))
            edges.append((dep, target))        # primero dep, despues target
            following[dep].append(target)
            indegree[target] += 1

    # Pasos 3 y 4: Kahn. 'ready' es una fila de atributos listos para calcular.
    ready = []
    for v in vertices:
        if indegree[v] == 0:
            ready.append(v)
    order = []
    while len(ready) > 0:
        key = ready.pop(0)
        if key in tasks:
            function, deps = tasks[key]
            values = []
            for dep_node, dep_attr in deps:
                values.append(dep_node.attrs[dep_attr])
            key[0].attrs[key[1]] = function(values)
        order.append(key)
        for successor in following[key]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)

    if len(order) != len(vertices):
        raise ValueError('Circular SDD: dependency graph contains a cycle')
    if main_attribute not in root.attrs:
        raise ValueError('Start attribute not computed: ' + main_attribute)
    return order, root.attrs[main_attribute], edges


# Imprime un nodo por linea, con sangria segun la profundidad.
def print_tree(root):
    pending = [(root, 0)]
    while len(pending) > 0:
        node, depth = pending.pop()
        parts = []
        for name in sorted(node.attrs):
            parts.append('{}={}'.format(name, node.attrs[name]))
        text = '  ' * depth + '{}{}'.format(node.symbol, node.number)
        if len(parts) > 0:
            text = text + ' [' + ', '.join(parts) + ']'
        print(text)
        i = len(node.children) - 1
        while i >= 0:
            pending.append((node.children[i], depth + 1))
            i -= 1


# Arbol sintactico de una palabra de la gramatica SDD (con nuestro parse_ll).
# Devuelve None si la palabra no pertenece al lenguaje.
def sdd_tree(word):
    first = first_sets(SDD_GRAMMAR, terminals_of(SDD_GRAMMAR))
    follow = follow_sets(SDD_GRAMMAR, first)
    table, valid = make_ll_table(SDD_GRAMMAR, first, follow)
    if not valid:
        raise ValueError('The chosen SDD grammar must be LL(1).')
    if word == EPS:
        word = ''
    return parse_ll(word, SDD_GRAMMAR, table)


# Modo --sdd: lee palabras (una por linea) hasta una linea vacia.
def run_sdd(show_graph=False):
    while True:
        try:
            line = input()
        except EOFError:
            break
        word = line.strip()
        if word == '':
            break
        root = sdd_tree(word)
        if root is None:
            print('no')
            continue
        try:
            order, value, edges = evaluate_sdd(root)
        except ValueError as error:
            print(error)
            return                       # SDD circular o con error: paramos
        print('Annotated parse tree:')
        print_tree(root)
        if show_graph:
            print('Dependency graph (source -> target):')
            names = []
            for key in order:
                names.append(attribute_name(key))
            print(' Vertices:', ', '.join(names))
            for source, target in edges:
                print(' ', attribute_name(source), '->', attribute_name(target))
        names = []
        for key in order:
            names.append(attribute_name(key))
        print('Evaluation order:', ' -> '.join(names))
        print('S.{} = {}'.format(SDD_MAIN, value))


# --cycle-demo: cambia TEMPORALMENTE una regla para que S.score dependa
# de si mismo. SDD_RULES original no se toca (trabajamos con una copia).
def cycle_demo():
    modified = dict(SDD_RULES)
    modified[('S', 'A')] = [
        Rule((0, 'level'), [], value_zero),
        Rule((-1, 'score'), [(-1, 'score')], add_one),
    ]
    print('Temporary change: S.score = S.score + 1')
    try:
        evaluate_sdd(sdd_tree('bdg'), modified)
    except ValueError as error:
        print(error)


# ======================================================================
# 5. DEMO Y PRUEBAS
# ======================================================================

# Calcula todo para una gramatica y lo devuelve en un diccionario.
def analyze(grammar):
    info = {}
    info['first'] = first_sets(grammar, terminals_of(grammar))
    info['follow'] = follow_sets(grammar, info['first'])
    info['ll'], info['ll_ok'] = make_ll_table(grammar, info['first'], info['follow'])
    (info['action'], info['goto'], info['prods'],
     info['states'], info['edges'], info['slr_ok']) = make_slr_table(grammar, info['follow'])
    return info


def ll_accepts(word, grammar, info):
    return parse_ll(word, grammar, info['ll']) is not None


def slr_accepts(word, grammar, info):
    return parse_slr(word, grammar, info['action'], info['goto'], info['prods']) is not None


# Devuelve el mensaje de error de evaluate_sdd ('' si no hubo error).
def sdd_error(word, rules):
    try:
        evaluate_sdd(sdd_tree(word), rules)
    except ValueError as error:
        return str(error)
    return ''


# --demo: ejemplos sin escribir nada.
def demo():
    print('DEMO 1: LL(1), epsilon, FIRST and FOLLOW')
    grammar = {'S': ['xAB'], 'A': ['aA', ''], 'B': ['bB', 'c']}
    info = analyze(grammar)
    for nt in sorted(grammar):
        print('First({}) = {}'.format(nt, set_text(info['first'][nt])))
        print('Follow({}) = {}'.format(nt, set_text(info['follow'][nt])))
    result = parse_ll('xaabc', grammar, info['ll'], True)
    print('Input xaabc:', 'yes' if result is not None else 'no')

    print('\nDEMO 2: left-recursive SLR(1), not LL(1)')
    grammar = {'S': ['S+a', 'a']}
    info = analyze(grammar)
    print('LL(1):', info['ll_ok'], '| SLR(1):', info['slr_ok'])
    result = parse_slr('a+a', grammar, info['action'], info['goto'], info['prods'], True)
    print('Input a+a:', 'yes' if result is not None else 'no')

    print('\nDEMO 3: SDD for abccdg')
    root = sdd_tree('abccdg')
    order, score, edges = evaluate_sdd(root)
    print_tree(root)
    names = []
    for key in order:
        names.append(attribute_name(key))
    print('Evaluation:', ' -> '.join(names))
    print('Dependency edges:', len(edges))
    print('S.score =', score)


# --test: pruebas simples. Cada una es (nombre, condicion que debe ser True).
def run_tests():
    checks = []

    # FIRST y FOLLOW con epsilon
    g1 = {'S': ['xAB'], 'A': ['aA', ''], 'B': ['bB', 'c']}
    i1 = analyze(g1)
    checks.append(('FIRST(A) = {a, e}', i1['first']['A'] == {'a', EPS}))
    checks.append(('FIRST(S) = {x}', i1['first']['S'] == {'x'}))
    checks.append(('FOLLOW(A) = {b, c}', i1['follow']['A'] == {'b', 'c'}))
    checks.append(('FOLLOW(B) = {$}', i1['follow']['B'] == {END}))

    # LL(1) y SLR(1) aceptan y rechazan lo mismo
    checks.append(('g1 es LL(1) y SLR(1)', i1['ll_ok'] and i1['slr_ok']))
    good = ['xc', 'xabc', 'xaabbc']
    bad = ['', 'xab', 'xcx', 'xacb']
    ok = True
    for w in good:
        if not (ll_accepts(w, g1, i1) and slr_accepts(w, g1, i1)):
            ok = False
    for w in bad:
        if ll_accepts(w, g1, i1) or slr_accepts(w, g1, i1):
            ok = False
    checks.append(('LL y SLR aceptan/rechazan bien', ok))

    # Recursion izquierda: solo SLR
    g2 = {'S': ['S+a', 'a']}
    i2 = analyze(g2)
    checks.append(('S -> S+a | a no es LL(1)', not i2['ll_ok']))
    checks.append(('S -> S+a | a es SLR(1)', i2['slr_ok']))
    checks.append(('a+a+a si, a++a no',
                   slr_accepts('a+a+a', g2, i2) and not slr_accepts('a++a', g2, i2)))

    # Ambigua: ninguno
    i3 = analyze({'S': ['SS', 'a']})
    checks.append(('S -> SS | a no es LL(1) ni SLR(1)', not i3['ll_ok'] and not i3['slr_ok']))

    # '@' es terminal valido
    g4 = {'S': ['@S', 'a']}
    i4 = analyze(g4)
    checks.append(('terminal @ funciona',
                   i4['ll_ok'] and i4['slr_ok']
                   and ll_accepts('@@a', g4, i4) and slr_accepts('@@a', g4, i4)))

    # Cadena vacia
    g5 = {'S': ['']}
    i5 = analyze(g5)
    checks.append(('S -> e acepta la cadena vacia',
                   ll_accepts('', g5, i5) and slr_accepts('', g5, i5)
                   and not ll_accepts('a', g5, i5)))

    # Ejemplos del enunciado
    g6 = {'S': ['AB'], 'A': ['aA', 'd'], 'B': ['bBc', '']}
    i6 = analyze(g6)
    checks.append(('Ejemplo 2 del enunciado',
                   i6['ll_ok'] and i6['slr_ok'] and ll_accepts('adbc', g6, i6)
                   and slr_accepts('d', g6, i6) and not ll_accepts('a', g6, i6)))
    g7 = {'S': ['S+T', 'T'], 'T': ['T*F', 'F'], 'F': ['(S)', 'i']}
    i7 = analyze(g7)
    checks.append(('Ejemplo 1 del enunciado',
                   (not i7['ll_ok']) and i7['slr_ok'] and slr_accepts('i+i', g7, i7)
                   and slr_accepts('(i)', g7, i7) and not slr_accepts('(i+i)*i)', g7, i7)))

    # SDD: valores
    cases = [('bdg', 3), ('bdffg', 5), ('abdg', 5), ('aabdg', 7), ('abccdg', 7)]
    ok = True
    for word, value in cases:
        root = sdd_tree(word)
        if root is None or evaluate_sdd(root)[1] != value:
            ok = False
    checks.append(('SDD: valores esperados', ok))
    checks.append(('SDD: "bd" no esta en el lenguaje', sdd_tree('bd') is None))

    # SDD: anidamiento profundo
    root = sdd_tree('a' * 1000 + 'bdg')
    checks.append(('SDD: 1000 letras a -> 2003', evaluate_sdd(root)[1] == 2003))

    # SDD: aristas respetan el orden
    root = sdd_tree('abdg')
    order, _, edges = evaluate_sdd(root)
    position = {}
    for i in range(len(order)):
        position[order[i]] = i
    ok = True
    for a, b in edges:
        if position[a] >= position[b]:
            ok = False
    checks.append(('SDD: cada dependencia va ANTES del atributo', ok))

    # SDD: ciclo
    cyc = dict(SDD_RULES)
    cyc[('S', 'A')] = [Rule((0, 'level'), [], value_zero),
                       Rule((-1, 'score'), [(-1, 'score')], copy_first)]
    checks.append(('SDD: detecta ciclo', 'Circular SDD' in sdd_error('bdg', cyc)))

    # SDD: atributo inexistente
    und = dict(SDD_RULES)
    und[('C', 'g')] = [Rule((-1, 'score'), [(0, 'missing')], value_one)]
    checks.append(('SDD: detecta atributo indefinido',
                   'Undefined attribute' in sdd_error('bdg', und)))

    failed = 0
    for name, ok in checks:
        if ok:
            print('  OK    ', name)
        else:
            print('  FALLA ', name)
            failed += 1
    print('{} pruebas, {} fallaron'.format(len(checks), failed))
    if failed > 0:
        sys.exit(1)


# ======================================================================
# 6. PROGRAMA PRINCIPAL
# ======================================================================

# Lee palabras (una por linea) hasta una linea vacia y dice yes / no.
# La letra 'e' sola significa la cadena vacia.
def parse_strings(choice, grammar, ll, action, goto, productions, trace):
    while True:
        try:
            line = input()
        except EOFError:
            break
        word = line.strip()
        if word == '':
            break
        if word == EPS:
            word = ''
        if choice == 'T':
            result = parse_ll(word, grammar, ll, trace)
        else:
            result = parse_slr(word, grammar, action, goto, productions, trace)
        if result is not None:
            print('yes')
        else:
            print('no')


def main():
    args = sys.argv[1:]

    if '--test' in args:
        run_tests()
        return
    if '--info' in args:
        print('Operating system:', platform.platform())
        print('Python version:', platform.python_version())
        return
    if '--demo' in args:
        demo()
        return
    if '--cycle-demo' in args:
        cycle_demo()
        return
    if '--sdd' in args:
        run_sdd('--graph' in args)
        return

    # Flujo normal: gramatica -> FIRST/FOLLOW -> tablas -> parser
    grammar = read_grammar()
    first = first_sets(grammar, terminals_of(grammar))
    follow = follow_sets(grammar, first)

    if '--sets' in args:
        for nt in sorted(grammar):
            print('First({}) = {}'.format(nt, set_text(first[nt])))
        for nt in sorted(grammar):
            print('Follow({}) = {}'.format(nt, set_text(follow[nt])))

    ll, ll_ok = make_ll_table(grammar, first, follow)
    action, goto, productions, states, edges, slr_ok = make_slr_table(grammar, follow)
    if '--table' in args:
        print_tables(ll, action, goto, productions, states, edges)

    if not ll_ok and not slr_ok:
        print('Grammar is neither LL(1) nor SLR(1).')
        return
    if ll_ok and not slr_ok:
        print('Grammar is LL(1).')
    if slr_ok and not ll_ok:
        print('Grammar is SLR(1).')

    trace = '--trace' in args
    while True:
        if ll_ok and slr_ok:
            print('Select a parser (T: for LL(1), B: for SLR(1), Q: quit):')
            try:
                choice = input().strip()
            except EOFError:
                break
            if choice == 'Q':
                break
            if choice != 'T' and choice != 'B':
                continue
        elif ll_ok:
            choice = 'T'
        else:
            choice = 'B'
        parse_strings(choice, grammar, ll, action, goto, productions, trace)
        if not (ll_ok and slr_ok):
            break


if __name__ == '__main__':
    main()
