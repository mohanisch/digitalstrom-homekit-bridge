# HomeKit Bridge für digitalStrom

Mit dieser Bridge ist es möglich, seine digitalStrom-Installation in HomeKit zu integrieren. 

Allerdings muss beachtet werden, dass die Ansätze von digitalStrom und HomeKit unterschiedlich sind. 

digitalStrom basiert grundsätzlich auf Szenen, unterstützt jedoch auch die Bedienung einzelner Geräte. HomeKit ist Geräte orientiert. 

Die Bridge versucht jedoch beide Welten zusammenzuführen. Werden Geräte, z.B. eine Lampe, in HomeKit bedient, wird zwischen Szenen und nicht-Szenen unterschieden. Schaltet HomeKit eine Lampe aus (Helligkeit = 0 %) bzw. ein (Helligkeit = 100 %), wird für dieses Gerät die entsprechende Szene geschaltet. Für Zonen/Räume gilt Ähnliches. Werden über eine HomeKit-Szene alle Geräte gleichen Typs angesprochen, dann wird jeweils die Szene des Raumes für ein/aus geschaltet. Erkennbar daran, dass z.B. alle Lampen gleichzeitig aus gehen und nicht nacheinander zeitversetzt. 

## Technische Voraussetzung
Es wird empfohlen, mindestens einen Raspberry Pi 3B+ zu verwenden.

## Unterstütze Geräte und Sensoren
Es werden alle Geräte mit konfigurierbaren Ausgang, Raumsensoren und zusätzlich noch 'Benutzerdefinierte Zustände' als konfigurierbarer Schalter unterstützt.
Die Benamung eine Gerätes setzt sich zusammen aus '<Raum> <Geräte Name>'. Heißt der Raum in HomeKit genauso wie in dS, wird der Raumname in HomeKit ausgeblendet.

Aktuell werden nur Licht- und Schatten-Klemmen unterstützt.

### Klemmen
Klemmen werden in HomeKit wie ein Gerät dargestellt. Es werden alle nötigen Eigenschaften übernommen, welche zur Steuerung notwendig sind. 
Ist z.B. eine gelbe Klemme dimmbar und im dS-Konfigurator als 'gedimmt' konfiguriert, lässt sich die Lampe auch über HomeKit dimmen. Ist jedoch die Klemme als 'geschaltet' konfiguriert, wird entsprechend nur ein 'Ein/Aus-Schalter' angezeigt.

Folgende Klemmen wurden bereits getestet.
- Schatten:
    - GR-KL200
- Licht: 
    - GE-TKM210
    - GE-SDM200
    - GE-KM200
    - GE-SDS200-CW

### Sensoren
Sind Räumen Sensoren zugeordnet, werden diese in HomeKit übernommen.
- Temperatur
- Luftfeuchtigkeit
- Bewegung
- Helligkeit

### Benutzerdefinierte Zustände
Im dS-Konfigurator können unzählig viele benutzerdefinierte Zustände angezeigt werden. Diese werden in HomeKit angezeigt, sobald die Option "Smartphone" im jeweiligen Zustand hinterlegt ist. Die Bridge stellt dann verschiedene Optionen zur Auswahl, wie dieser Zustand angezeigt werden soll (z.B. als Schalter, Sprinkler, ...).  

### Hue Integration
Ebenfalls funktionieren Lampen, die über Philips Hue bzw. Plan44 eingebunden werden. Ein kleiner Benefit ist hier, dass bei nicht Hue zertifizierten Geräten die Auswahl der Farbe über die Home-App möglich ist (aktuell nicht möglich über die dS-App). 
Folgende Lampen wurden bereits getestet:
- Philips Hue White and Color
- Philips Hue White Ambiance
- Livarno Lux LED Strip
- Ikea Tradfri

### Virtuelle Devices über Plan44
Bisher konnten erfolgreich folgende virtuelle Devices getestet werden (wenn mit Ausgang erstellt):
- Gelbe Klemmen

Virtuelle schwarze Klemmen zwar auch erkannt, jedoch lassen sich diese Klemmen aktuell nicht über die API von dS steuern, da scheinbar die Implementierung fehlerhaft ist und kein standardisierter Ausgang der Klemme zur Verfügung steht. 

## Setup
### Docker
```
docker run -d \
    --name=dsbridge \
    --network=host \
    --volume dsbridge-data:/data \
    --volume dsbridge-config:/config \
    -e CONFIG_PATH=/config \
    -e PERSIST_FILE_PATH=/data \
    -e HOSTNAME=10.11.12.200 \
    marcohanisch/digitalstrom-homekit-bridge:latest 
```

### pip
```
pip install dsbridge
dsbridge \ 
  --hostname 10.11.12.200 \
  --persit-file-path /opt/dsbrdige/data \
  --config-path /opt/dsbrdige/conf > /dev/null &


```

dsHomekit

##Install
python3 setup.py build
python3 setup.py install

##Start app
$ dsHomekit

