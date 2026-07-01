# Ortomosaico DJI com OpenDroneMap/ODM

Projeto local para geração de ortomosaicos a partir de imagens capturadas com drone DJI, usando **OpenDroneMap/ODM** via Docker.

https://github.com/OpenDroneMap/ODM/blob/master/README.md

O objetivo principal é processar imagens aéreas com metadados EXIF/GPS e gerar um **ortomosaico final em GeoTIFF (`.tif`)**, pronto para uso em QGIS, ArcGIS ou outros softwares GIS.

---

## Visão geral

O script Python não implementa a fotogrametria diretamente. Ele atua como um orquestrador para o OpenDroneMap:

```text
Imagens DJI
  ↓
Script Python organiza o projeto
  ↓
Docker executa OpenDroneMap/ODM
  ↓
ODM processa fotogrametria, reconstrução e ortofoto
  ↓
Script copia o GeoTIFF final para a pasta de saída
```

O pipeline interno do ODM passa por etapas como:

```text
opensfm
openmvs
odm_filterpoints
odm_meshing
mvs_texturing
odm_orthophoto
```

---

## Estrutura esperada

Exemplo de organização usada no projeto:

```text
ortomosaico/
  imagens/
    ortomosaico-80mm-full/
      DJI_0001.JPG
      DJI_0002.JPG
      DJI_0003.JPG

  scripts/
    generate_orthomosaic.py

  tiff/
    high_80m_1cm/
      ortomosaico_dji_air3s_orthomosaic.tif
```

A pasta de trabalho pesada do ODM fica em outro disco:

```text
/home/savefarm/HD/ortomosaico/odm_projects/
```

Dentro dela, o ODM cria:

```text
odm_projects/
  ortomosaico_dji_air3s/
    images/
    opensfm/
    odm_filterpoints/
    odm_meshing/
    odm_texturing_25d/
    odm_orthophoto/
    odm_report/
```

---

## Requisitos

### Sistema

* Linux/Ubuntu
* Docker instalado
* Espaço em disco disponível
* RAM alta recomendada
* CPU multicore recomendada

### Docker

Verificar instalação:

```bash
docker --version
```

Baixar imagem ODM:

```bash
docker pull opendronemap/odm
```

---

## Como executar

Na raiz do projeto ou na pasta do script:

```bash
python scripts/generate_orthomosaic.py
```

Ou usando ambiente conda:

```bash
conda run -n yolo python scripts/generate_orthomosaic.py
```

---

## Principais parâmetros

### Caminhos

```python
INPUT_IMAGES_DIR
```

Pasta onde estão as imagens originais do drone.

```python
PROJECTS_ROOT
```

Pasta onde o ODM cria os arquivos intermediários do processamento.

```python
PROJECT_NAME
```

Nome do projeto ODM. Também define a subpasta dentro de `PROJECTS_ROOT`.

```python
FINAL_OUTPUT_DIR
```

Pasta onde o ortomosaico final será copiado.

---

## Parâmetros de qualidade

```python
ORTHOPHOTO_RESOLUTION_CM = 1.0
```

Define a resolução final do ortomosaico.

```text
1.0 = 1 cm/pixel
2.0 = 2 cm/pixel
5.0 = 5 cm/pixel
```

Quanto menor o valor, maior a resolução, mas maior o tempo, uso de RAM e espaço em disco.

---

```python
FEATURE_QUALITY = "high"
```

Controla a qualidade das features usadas para alinhar as imagens.

Valores comuns:

```text
lowest
low
medium
high
ultra
```

---

```python
POINT_CLOUD_QUALITY = "high"
```

Controla a qualidade da reconstrução densa/nuvem de pontos.

Valores mais altos aumentam qualidade, mas também aumentam RAM, tempo e espaço em disco.

---

## Parâmetros de desempenho

```python
MAX_CONCURRENCY = 8
```

Controla quantas tarefas/threads o ODM pode executar em paralelo.

Valores maiores podem acelerar algumas etapas, mas aumentam o risco de falta de memória.

Recomendação prática:

```text
8  = mais seguro para datasets grandes
16 = intermediário
32 = pesado
64 = alto risco de erro por falta de RAM
```

Em datasets grandes com imagens DJI de 8192 px, valores muito altos podem causar erro `137`.

---

## Modelo 3D

```python
SKIP_3D_MODEL = True
```

Pula a geração do modelo 3D final.

Para uso agrícola focado em ortomosaico, normalmente é recomendado deixar como `True`.

---

## Fast orthophoto

```python
FAST_ORTHOPHOTO = False
```

Quando `True`, gera uma ortofoto mais rápida e leve, mas com possível perda de qualidade.

Uso recomendado:

```text
False = melhor qualidade
True  = mais rápido e mais leve
```

---

## GeoTIFF otimizado

```python
CREATE_COG = True
BUILD_OVERVIEWS = True
```

Esses parâmetros ajudam a gerar um GeoTIFF mais adequado para uso em GIS.

```python
CREATE_COG = True
```

Gera Cloud Optimized GeoTIFF.

```python
BUILD_OVERVIEWS = True
```

Cria pirâmides/overviews para abrir o arquivo mais rapidamente no QGIS.

---

## Recorte automático

```python
AUTO_BOUNDARY = True
```

Permite que o ODM tente cortar automaticamente as bordas do ortomosaico.

---

## DSM e DTM

```python
CREATE_DSM = False
CREATE_DTM = False
```

Por padrão, o projeto gera apenas o ortomosaico.

Para gerar modelos de elevação:

```python
CREATE_DSM = True
CREATE_DTM = True
```

Diferença:

```text
DSM = superfície com solo, plantas, árvores e objetos
DTM = tentativa de representar apenas o terreno
```

---

## Continuar processamento após falha

O ODM pode falhar por falta de RAM em etapas avançadas. O erro mais comum observado foi:

```text
Child returned 137
Whoops! You ran out of memory!
```

Para continuar a partir da etapa de texturização:

```python
RERUN_FROM = "mvs_texturing"
CLEAN_PROJECT_IMAGES = False
CLEAN_OLD_PROCESSING = False
```

Para rodar tudo do zero:

```python
RERUN_FROM = None
CLEAN_PROJECT_IMAGES = True
CLEAN_OLD_PROCESSING = True
```

Atenção: use `None` sem aspas.

Correto:

```python
RERUN_FROM = None
```

Errado:

```python
RERUN_FROM = "None"
```

---

## Redução de RAM na texturização

Em datasets grandes, o processo pode morrer na etapa:

```text
Running local seam leveling
Killed
```

Para evitar isso:

```python
TEXTURING_SKIP_LOCAL_SEAM_LEVELING = True
```

Esse parâmetro pula a correção local de emendas da textura.

Vantagem:

```text
Menos RAM
Maior chance de terminar
```

Desvantagem:

```text
Pode deixar algumas emendas mais visíveis no ortomosaico
```

Se ainda faltar RAM:

```python
TEXTURING_SKIP_GLOBAL_SEAM_LEVELING = True
```

Esse segundo parâmetro reduz ainda mais o acabamento de cor, mas pode permitir finalizar o processamento.

---

## Hardlink e uso de espaço

O script tenta usar hardlink para evitar duplicar as imagens dentro da pasta do projeto ODM:

```python
USE_HARDLINK_OR_COPY = True
```

Se o hardlink funcionar, as imagens aparecem em:

```text
pasta_original/
odm_projects/projeto/images/
```

mas não são duplicadas fisicamente no disco.

Para verificar se é hardlink:

```bash
ls -li caminho/original/DJI_0001.JPG
ls -li caminho/odm_projects/projeto/images/DJI_0001.JPG
```

Se o inode for igual, é o mesmo arquivo físico.

---

## Monitoramento durante o processamento

### Ver uso do container Docker

```bash
docker stats
```

### Ver uso de CPU/RAM

```bash
btop
```

### Ver espaço livre

```bash
df -h
```

### Ver tamanho do projeto ODM

```bash
sudo du -h --max-depth=1 "/home/savefarm/HD/ortomosaico/odm_projects/ortomosaico_dji_air3s" | sort -h
```

### Monitorar pasta de texturização

```bash
watch -n 10 'du -sh "/home/savefarm/HD/ortomosaico/odm_projects/ortomosaico_dji_air3s/odm_texturing_25d"'
```

---

## Saída final

O arquivo final principal é um GeoTIFF:

```text
ortomosaico_dji_air3s_orthomosaic.tif
```

Ele é copiado para:

```python
FINAL_OUTPUT_DIR
```

Exemplo:

```text
/home/savefarm/Documents/Estudo Crop/ortomosaico/tiff/high_80m_1cm/
```

---

## Arquivos intermediários

A pasta do projeto ODM pode ficar muito grande.

Principais pastas geradas:

```text
opensfm/
odm_filterpoints/
odm_meshing/
odm_texturing_25d/
odm_orthophoto/
odm_report/
```

Depois que o `.tif` final for salvo e conferido, a pasta do projeto pode ser apagada para liberar espaço:

```bash
rm -rf "/home/savefarm/HD/ortomosaico/odm_projects/ortomosaico_dji_air3s"
```

---

## Configuração recomendada para dataset grande

Para imagens DJI grandes, por exemplo 8192 px, configuração segura:

```python
ORTHOPHOTO_RESOLUTION_CM = 1.0
FEATURE_QUALITY = "high"
POINT_CLOUD_QUALITY = "high"
MAX_CONCURRENCY = 8

SKIP_3D_MODEL = True
FAST_ORTHOPHOTO = False

CREATE_COG = True
BUILD_OVERVIEWS = True
AUTO_BOUNDARY = True

CREATE_DSM = False
CREATE_DTM = False

TEXTURING_SKIP_LOCAL_SEAM_LEVELING = True
TEXTURING_SKIP_GLOBAL_SEAM_LEVELING = False
```

Se ainda ocorrer erro de RAM:

```python
MAX_CONCURRENCY = 8
TEXTURING_SKIP_LOCAL_SEAM_LEVELING = True
TEXTURING_SKIP_GLOBAL_SEAM_LEVELING = True
```

Ou reduzir a resolução:

```python
ORTHOPHOTO_RESOLUTION_CM = 2.0
```

---

## Uso de GPU

Foi testada a possibilidade de usar:

```python
ODM_DOCKER_IMAGE = "opendronemap/odm:gpu"
```

com:

```bash
--gpus all
```

Porém, houve erro de compatibilidade CUDA/driver:

```text
unsatisfied condition: cuda>=12.9
please update your driver to a newer version, or use an earlier cuda container
```

Por isso, a versão atual do projeto utiliza:

```python
ODM_DOCKER_IMAGE = "opendronemap/odm"
```

ou seja, execução em CPU.

---

## Observações importantes

* Não versionar imagens, GeoTIFFs ou projetos ODM no Git.
* Guardar no Git apenas scripts, configurações e documentação.
* Para cada novo lote de imagens, usar um novo `PROJECT_NAME` ou limpar corretamente o processamento antigo.
* Para continuar após falha, não apagar `images/`, `opensfm/` ou demais etapas já processadas.
* O erro `137` normalmente indica falta de memória RAM.
* Reduzir `MAX_CONCURRENCY` diminui uso de RAM, mas aumenta o tempo de processamento.
* Pular `local seam leveling` pode reduzir qualidade visual das emendas, mas aumenta a chance de finalizar o ortomosaico.

---
