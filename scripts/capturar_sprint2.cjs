// QA local; requiere Playwright disponible. No navega al despliegue público.
const { chromium } = require('playwright');
const path = require('path');
let page;
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHANNEL} : {})});
  page = await browser.newPage({viewport:{width:1440,height:1080}});
  const errores = [];
  page.on('pageerror', error => errores.push(error.message));
  await page.goto('http://localhost:8502', {waitUntil:'networkidle'});
  await page.getByRole('button', {name:'Cargar caso esperado', exact:true}).click();
  await page.getByRole('tab', {name:'4 Analizar',exact:true}).click();
  await page.getByText('ALERTAS RELEVANTES', {exact:true}).first().waitFor();
  await page.waitForTimeout(800);
  await page.screenshot({path:path.join(__dirname,'../docs/evidencias-sprint2/pantalla-analisis.png'),fullPage:true});
  await page.getByRole('tab', {name:'2 Evidencias',exact:true}).click();
  await page.getByText('Confirmo que todos los archivos son sintéticos/anónimos y no contienen datos reales', {exact:true}).click();
  await page.waitForTimeout(800); // Esperar rerun que habilita el uploader.
  await page.locator('input[type=file]').setInputFiles([8,9,10].map(m => path.join(__dirname,`../docs/evidencias-sprint2/boleta-sintetica-2026-${String(m).padStart(2,'0')}.pdf`)));
  await page.waitForTimeout(1200); // Esperar subida y rerun antes del botón de lectura.
  await page.getByRole('button', {name:'Leer archivos localmente',exact:true}).click();
  await page.getByText(/documento-[a-f0-9]+\.pdf/).first().waitFor({timeout:30000});
  await page.getByRole('tab', {name:'3 Confirmar',exact:true}).click();
  await page.getByRole('button', {name:'Confirmar transcripción',exact:true}).first().waitFor();
  await page.waitForTimeout(800);
  await page.screenshot({path:path.join(__dirname,'../docs/evidencias-sprint2/pantalla-confirmacion.png'),fullPage:true});
  if (await page.locator('[data-testid="stException"]').count()) throw new Error('Excepción de Streamlit');
  if (errores.length) throw new Error(errores.join('\n'));
  console.log('Navegador: carga, análisis, subida de tres PDF y confirmación pendiente verificados.');
  await browser.close();
})().catch(async error => {if(page) {await page.screenshot({path:path.join(__dirname,'../../sprint2-debug.png'),fullPage:true}); console.log((await page.locator('body').innerText()).slice(-5000));} console.error(error); process.exit(1);});
