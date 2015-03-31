 #!/bin/bash
 #You need lingua and gettext installed to run this
 
 echo "Updating Arche.pot"
 pot-create -d Arche -o Arche.pot ../.
 echo "Merging Swedish localisation"
 msgmerge --update sv/LC_MESSAGES/Arche.po Arche.pot
 echo "Updated locale files"
 
 