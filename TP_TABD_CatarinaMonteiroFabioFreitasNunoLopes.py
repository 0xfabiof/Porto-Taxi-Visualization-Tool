from urllib import pathname2url
import os, webbrowser

import gmplot

from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt

import psycopg2


psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

## Lista de Cores a usar nos plots
colors = ['red','blue','green','purple','yellow','brown','orange']

## Geracao mapa API google maps - coords centro e zoom
gmap = gmplot.GoogleMapPlotter(41.1628517,-8.6216608,13)



def dbconnect():
        conn=psycopg2.connect("dbname=taxis user=fabio password=toor")
        conn.autocommit = True
        return conn.cursor()

def lista_freguesias(cur):
        ## Criacao de lista de freguesias no concelho do porto
        cur.execute("select distinct freguesia from cont_aad_caop2017 where concelho ilike 'porto'")
        freguesias=cur.fetchall()
        return freguesias

def gmaps_taxi_stands_marker(cur):
        ## Geracao de marcadores nas pracas de taxi (taxi_stands)
        cur.execute("Select st_y(location),st_x(location) from taxi_stands")
        results=cur.fetchall()
        for row in results:
                gmap.marker(row[0],row[1])

def gmaps_freguesia_constructor(cur):


        ## Ciclo para desenho do poligno de contorno de cada freguesia
        i=0
        for freguesia in freguesias:

                freg_long_list=[]
                freg_lat_list=[]

                # Query retorna os pontos que compoe o poligno (simplificados) - feito o parsing para obter as coordenadas
                cur.execute("select st_dumppoints(st_simplify(geom,0.0001)) from cont_aad_caop2017 where freguesia ilike '%s' AND concelho ilike 'porto'" % freguesia)
                results=cur.fetchall()
                for row in results:
                        a=str(row[0]).split(',')
                        a[3]=a[3].replace(')','')
                        a[3]=a[3].replace('\'','')

                        cur.execute("select st_y('%s'),st_x('%s')" % (a[3],a[3]))
                        results2=cur.fetchall()
                        for row in results2:
                                freg_long_list.append(row[0])
                                freg_lat_list.append(row[1])

                gmap.plot(freg_long_list,freg_lat_list,colors[i],edge_width=7)
                i+=1

def gmaps_heat(cur):
        ##funcao que cria heatmap com as cordenadas x e y da lista de pontos (initial_point)

        sqlquery1='select st_y(initial_point),st_x(initial_point) from taxi_services limit 10000'
        cur.execute(sqlquery1)
        heatmap=cur.fetchall()
        heat_long_list=[]
        heat_lat_list=[]
        for ponto in heatmap:
                heat_long_list.append(ponto[0])
                heat_lat_list.append(ponto[1])

        gmap.heatmap(heat_long_list,heat_lat_list)

def gmaps_generate(cur):
        gmaps_taxi_stands_marker(cur)
        gmaps_freguesia_constructor(cur)
        gmaps_heat(cur)
        gmap.draw("mapa.html")
        url = 'file:{}'.format(pathname2url(os.path.abspath('mapa.html')))
        webbrowser.open(url)

def plot_3D_altitude(cur):
        ## Configuracao do tamanho da figura e dos eixos 3d
        fig = plt.figure(figsize=(15,10))
        ax = fig.add_subplot(111, projection='3d')
        ax.set_zlim(0, 595000)

        ## auxiliar_1 - tabela com atributos freguesia, ponto de centro, numero de servicos iniciados e finalizados nela
        tabela_auxiliar(cur)

        ## Ciclo para desenho do poligno de contorno de cada freguesia - desta vez fora das tiles do googlemaps
        i = 0
        label=[]
        for freguesia in freguesias:
                ## Queries para geracao do grafico 3D. IP para initial_points e FP para final_points
                
                sqlqueryIP = ("select st_y(st_centroid), st_x(st_centroid), inicios,freguesia from auxiliar_1 where freguesia ilike '%s'" % freguesia)
                sqlqueryFP = ("select st_y(st_centroid), st_x(st_centroid), fins,freguesia from auxiliar_1 where freguesia ilike '%s'" % freguesia)

                freg_long_list=[]
                freg_lat_list=[]

                # Query retorna os pontos que compoe o poligno (simplificados) - feito o parsing para obter as coordenadas
                cur.execute("select st_dumppoints(st_simplify(geom,0.0001)) from cont_aad_caop2017 where freguesia ilike '%s' AND concelho ilike 'porto'" % freguesia)
                results=cur.fetchall()
                for row in results:
                        a=str(row[0]).split(',')
                        a[3]=a[3].replace(')','')
                        a[3]=a[3].replace('\'','')

                        cur.execute("select st_y('%s'),st_x('%s')" % (a[3],a[3]))
                        results2=cur.fetchall()
                        for row in results2:
                                freg_long_list.append(row[0])
                                freg_lat_list.append(row[1])


                ## execucao da query que retorna os resultados a serem usados na geracao do grafico
                cur.execute(sqlqueryIP)
                results3=cur.fetchall()
                for row in results3:
                        centro_lon=row[0]
                        centro_lat=row[1]
                        count=row[2]
                        nome=row[3]

                ## Desenho do poligno da freguesia com a cor da lista e etiqueta correspondente
                ax.plot(freg_lat_list,freg_long_list, color=colors[i], label="%s : %d" % (nome,count))

                ## Desenho das barras 3d usando a contagem de servicos iniciados como eixo z
                ax.bar3d(centro_lat, centro_lon , 0, 0.002, 0.001, count, color=colors[i], alpha=0.8)
                i+=1


        plt.legend(prop={'size': 6.5},loc='lower right')

        plt.show()

def tabela_auxiliar(cur):
        ## auxiliar_1 - tabela com atributos freguesia, ponto de centro, numero de servicos iniciados e finalizados nela
        ## try_except verifica se a tabela ja existe - se nao existe e criada
        try:
                cur.execute("select exists(select * from auxiliar_1 limit 1)")
        except:
                cur.execute("create table auxiliar_1 as select x.freguesia,x.st_centroid,a as inicios, b as fins from (select freguesia, st_centroid(geom), count(initial_point) as a from taxi_services, cont_aad_caop2017 where ST_contains(geom,initial_point) AND concelho ilike 'porto' group by 1,2) as x, (select freguesia, st_centroid(geom), count(final_point) as b from taxi_services, cont_aad_caop2017 where ST_contains(geom,final_point) and concelho ilike 'porto' group by 1,2) as y where x.freguesia=y.freguesia and x.st_centroid=y.st_centroid group by 1,2,3,4")


def menu():
        choice = input("Escolha uma opcao:\n1: Heatmap de servicos no concelho do Porto (Baseado na API Google Maps\n2: Contagem de servicos por freguesia (Projeccao 3D)\n3: Criar ambas as vizualizacoes. \n")
        if choice == 1:
                gmaps_generate(cur)
        elif choice == 2:
                plot_3D_altitude(cur)
        elif choice == 3:
                gmaps_generate(cur)
                plot_3D_altitude(cur)
        else:
                print("Escolha uma opcao valida")


# conexao a db armazenada na variavel cur
cur=dbconnect()

# lista de freguesias armazenada na variavel freguesias
freguesias=lista_freguesias(cur)

menu()