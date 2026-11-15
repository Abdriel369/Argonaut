"""La página principal muestra la tripulación y /reloj/ se sirve sin 404."""

import asyncio

import pila


def test_la_pagina_principal_incluye_la_seccion_crew_y_el_enlace_al_reloj():
    async def caso():
        async with pila.navegador(pila.crear_pila(laptop3_apagada=True)) as nav:
            return await nav.get("/")

    respuesta = asyncio.run(caso())
    assert respuesta.status_code == 200
    assert 'id="sec-tripulacion"' in respuesta.text
    assert 'href="reloj/"' in respuesta.text
    assert "tripulacion.css" in respuesta.text


def test_la_pagina_del_reloj_se_sirve_por_la_misma_aplicacion():
    async def caso():
        async with pila.navegador(pila.crear_pila(laptop3_apagada=True)) as nav:
            sin_barra = await nav.get("/reloj", follow_redirects=False)
            con_barra = await nav.get("/reloj/")
            return sin_barra, con_barra

    sin_barra, con_barra = asyncio.run(caso())
    assert sin_barra.status_code in (301, 302, 307, 308)
    assert con_barra.status_code == 200
    assert "Simulated data. Not a medical diagnosis." in con_barra.text
    assert 'data-pantalla-nav="tendencia"' in con_barra.text
