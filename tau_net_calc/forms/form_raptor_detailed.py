import os
import cProfile
import pstats
import io
import webbrowser
import re
import configparser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )
from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QDateTime,
                          QEvent,
                          QVariant
                          )
from PyQt5.QtGui import QRegExpValidator, QDesktopServices
from PyQt5 import uic

from query_file import runRaptorWithProtocol, myload_all_dict
from tau_net_calc.cls.common import (getDateTime, 
                    get_qgis_info, 
                    is_valid_folder_name, 
                    get_prefix_alias, 
                    seconds_to_time, 
                    time_to_seconds, 
                    check_file_parameters_accessibility
                    )
from stat_destination import DayStat_DestinationID
from stat_from_to import StatFromTo

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'raptor.ui')
)

class RaptorDetailed(QDialog, FORM_CLASS):
    def __init__(self, parent, mode, protocol_type, title, timetable_mode):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        fix_size = 15* self.txtMinTransfers.fontMetrics().width('x')

        self.txtMinTransfers.setFixedWidth(fix_size)
        self.txtMaxTransfers.setFixedWidth(fix_size)
        self.txtMaxWalkDist1.setFixedWidth(fix_size)
        self.txtMaxWalkDist2.setFixedWidth(fix_size)
        self.txtMaxWalkDist3.setFixedWidth(fix_size)

        self.dtStartTime.setFixedWidth(fix_size)

        self.txtDepartureInterval.setFixedWidth(fix_size)
        self.txtMaxExtraTime.setFixedWidth(fix_size)
        self.txtSpeed.setFixedWidth(fix_size)
        self.txtMaxWaitTime.setFixedWidth(fix_size)

        self.txtMaxWaitTimeTransfer.setFixedWidth(fix_size)
        self.txtMaxTimeTravel.setFixedWidth(fix_size)
        self.txtTimeInterval.setFixedWidth(fix_size)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.shift_mode = False
        self.shift_ctrl_mode =  False

        self.parent = parent
        self.mode = mode
        self.protocol_type = protocol_type
        self.title = title
        self.timetable_mode = timetable_mode
        # self.change_time = 1

        self.progressBar.setValue(0)

        if self.protocol_type == 2:
            self.txtTimeInterval.setVisible(False)
            self.lblTimeInterval.setVisible(False)
            parent_layout = self.horizontalLayout_16.parent()
            parent_layout.removeItem(self.horizontalLayout_16)

        if self.protocol_type == 2:
            self.cmbFields_ch.setVisible(False)
            self.lblFields.setVisible(False)

            parent_layout = self.horizontalLayout_6.parent()
            parent_layout.removeItem(self.horizontalLayout_6)

        if not timetable_mode:

            self.lblMaxExtraTime.setVisible(False)
            self.txtMaxExtraTime.setVisible(False)
            self.lblDepartureInterval.setVisible(False)
            self.txtDepartureInterval.setVisible(False)
            
            parent_layout = self.horizontalLayout_11.parent()
            parent_layout.removeItem(self.horizontalLayout_11)

        if timetable_mode:
            self.lblMaxWaitTime.setVisible(False)
            self.txtMaxWaitTime.setVisible(False)
            parent_layout = self.horizontalLayout_13.parent()
            parent_layout.removeItem(self.horizontalLayout_13)
        
        if self.mode == 2:
            self.label_21.setText("Arrive before (hh:mm:ss)")
            self.label_17.setText("Layer of origins")
            self.label_5.setText("Layer of facilities")
        
        if self.protocol_type == 1:    
            if self.mode == 2:
                self.label_5.setText("Layer of all destinations in the region")
            if self.mode == 1:    
                self.label_17.setText("Layer of all origins in the region")


        # THE EXPERIMENT - CANCEL DepartureInterval for TIMETABLE MODE
        self.lblDepartureInterval.setVisible(False)
        self.txtDepartureInterval.setVisible(False)
        parent_layout = self.horizontalLayout_10.parent()
        parent_layout.removeItem(self.horizontalLayout_10)

        if timetable_mode and self.mode == 1:
            self.label_21.setText("Earliest start time")
            self.lblMaxExtraTime.setText("Latest start time is T minutes later, T =")
            
        if timetable_mode and self.mode == 2:

            self.label_21.setText("Earliest arrival time")
            self.lblMaxExtraTime.setText(
                "Latest arrival time is T minutes later, T = ")
            
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_PKL.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToPKL))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))

        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)
        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayersDest)
        self.cmbLayersDest.installEventFilter(self)
        self.showAllLayersInCombo_Polygon(self.cmbVizLayers)
        self.cmbVizLayers.installEventFilter(self)
        self.dtStartTime.installEventFilter(self)

        self.cmbLayers_fields.installEventFilter(self)
        self.cmbLayersDest_fields.installEventFilter(self)
        self.cmbVizLayers_fields.installEventFilter(self)

        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)
        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers, self.cmbLayers_fields))

        self.fillComboBoxFields_Id(
            self.cmbLayersDest, self.cmbLayersDest_fields)
        self.cmbLayersDest.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayersDest, self.cmbLayersDest_fields))

        self.fillComboBoxFields_Id(self.cmbVizLayers, self.cmbVizLayers_fields)
        self.cmbVizLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbVizLayers, self.cmbVizLayers_fields))

        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton(
            "Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton(
            "Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton(
            "Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        #  create a regular expression instance for integers
        regex1 = QRegExp(r"\d*")

        int_validator1 = QRegExpValidator(regex1)

        # 0,1,2
        regex2 = QRegExp(r"[0-2]{1}")
        int_validator2 = QRegExpValidator(regex2)

        # floating, two digit after dot
        regex3 = QRegExp(r"^\d+(\.\d{1,2})?$")
        int_validator3 = QRegExpValidator(regex3)

        self.txtMinTransfers.setValidator(int_validator2)
        self.txtMaxTransfers.setValidator(int_validator2)
        self.txtMaxWalkDist1.setValidator(int_validator1)
        self.txtMaxWalkDist2.setValidator(int_validator1)
        self.txtMaxWalkDist3.setValidator(int_validator1)
        self.txtSpeed.setValidator(int_validator3)
        self.txtMaxWaitTime.setValidator(int_validator3)
        self.txtMaxWaitTimeTransfer.setValidator(int_validator3)
        self.txtMaxTimeTravel.setValidator(int_validator3)
        self.txtMaxExtraTime.setValidator(int_validator3)
        self.txtDepartureInterval.setValidator(int_validator3)
        
        

        
        self.default_alias = get_prefix_alias(True, 
                                self.protocol_type, 
                                self.mode, 
                                self.timetable_mode, 
                                full_prefix=False)
        
        self.ParametrsShow()

    """
    def keyPressEvent(self, event):
        
        if event.modifiers() & Qt.ShiftModifier:
            self.run_button.setStyleSheet("color: green; font-weight: bold;")
            self.run_button.repaint()

        if event.modifiers() & Qt.ShiftModifier and event.modifiers() & Qt.ControlModifier:
            self.run_button.setStyleSheet("color: red;")  
            self.run_button.repaint()    

    def keyReleaseEvent(self, event):
        
        self.run_button.setStyleSheet("color: black;")  
        self.run_button.repaint()
    """

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields):
        obj_layer_fields.clear()
        selected_layer_name = obj_layers.currentText()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)

        if not layers:
            return
        layer = layers[0]

        fields = layer.fields()
        osm_id_exists = False

        # regular expression to check for the presence of only digit
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                # add numeric fields
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == "osm_id":
                    osm_id_exists = True
            elif field_type == QVariant.String:
                # check the first value of the field for digits only
                first_value = None
                for feature in layer.getFeatures():
                    first_value = feature[field_name]
                    break  # stop after the first value

                if first_value is not None and digit_pattern.match(str(first_value)):
                    obj_layer_fields.addItem(field_name)
                    if field_name.lower() == "osm_id":
                        osm_id_exists = True

        if osm_id_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == "osm_id":
                    obj_layer_fields.setCurrentIndex(i)
                    break

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def checkLayer_type(self, layer_name):
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        if layer.wkbType() != 1:  # QgsWkbTypes.PointGeometry:
            return 0
        else:
            return 1

    def on_run_button_clicked(self):

        modifiers = QGuiApplication.keyboardModifiers()
        if (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier) and self.protocol_type == 2:
            self.shift_mode = True

        if modifiers == (Qt.ShiftModifier | Qt.ControlModifier) and self.protocol_type == 2 and self.mode == 1 :
            self.shift_ctrl_mode = True    

        self.run_button.setEnabled(False)
        self.break_on = False

        if not (is_valid_folder_name(self.txtAliase.text())):
            self.setMessage(f"'{self.txtAliase.text()}' is not a valid directory/file name")
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if not self.cmbLayers.currentText():
            self.run_button.setEnabled(True)
            self.setMessage("Choose layer")
            return 0

        self.folder_name = f'{self.txtPathToProtocols.text()}//{self.txtAliase.text()}'
        self.aliase = self.txtAliase.text()

        self.saveParameters()
        self.readParameters()

        self.setMessage("Starting ...")
        self.close_button.setEnabled(False)
        self.textLog.clear()
        self.tabWidget.setCurrentIndex(1)
        self.textLog.append("<a style='font-weight:bold;'>[System]</a>")
        qgis_info = get_qgis_info()

        info_str = "<br>".join(
            [f"{key}: {value}" for key, value in qgis_info.items()])
        self.textLog.append(f'<a> {info_str}</a>')
        self.textLog.append("<a style='font-weight:bold;'>[Mode]</a>")
        self.textLog.append(f'<a> Mode: {self.title}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f'<a> Output alias: {self.aliase}</a>')
        self.textLog.append(f"<a> Transit routing database folder: {self.config['Settings']['pathtopkl']}</a>")
        self.textLog.append(f"<a> Output folder: {self.config['Settings']['pathtoprotocols']}</a>")
        
        if self.protocol_type == 2:
            if self.mode == 1:
                name1 = "facilities"
                name2 = "destinations"
            else:
                name2 = "facilities"
                name1 = "origins"

        if self.protocol_type == 1:
            if self.mode == 1:
                name1 = "all origins in the region"
                name2 = "destinations"
            else:
                name2 = "all destinations in the region"
                name1 = "origins"    
        self.textLog.append(f'<a> Layer of {name1}: {self.layer_origins_path}</a>')
        self.textLog.append(f"<a> Selected {name1}: {self.config['Settings']['SelectedOnly1']}</a>")
        self.textLog.append(f'<a> Layer of {name2}: {self.layer_destinations_path}</a>')
        self.textLog.append(f"<a> Selected {name2}: {self.config['Settings']['SelectedOnly2']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Parameters of a trip]</a>")
        self.textLog.append(f"<a> Aerial distance: {self.config['Settings']['RunOnAir']}</a>")
        self.textLog.append(f"<a> Minimum number of transfers: {self.config['Settings']['min_transfer']}</a>")
        self.textLog.append(f"<a> Maximum number of transfers: {self.config['Settings']['max_transfer']}</a>")
        self.textLog.append(f"<a> Maximum walk distance to the initial PT stop: {self.config['Settings']['maxwalkdist1']} m</a>")

        self.textLog.append(f"<a> Maximum walk distance between at the transfer: {self.config['Settings']['maxwalkdist2']} m</a>")
        self.textLog.append(f"<a> Maximum walk distance from the last PT stop: {self.config['Settings']['maxwalkdist3']} m</a>")
        self.textLog.append(f"<a> Walking speed: {self.config['Settings']['speed']} km/h</a>")

        if not self.timetable_mode:
            self.textLog.append(f"<a> Maximum waiting time at the initial stop: {self.config['Settings']['maxwaittime']} min</a>")

        self.textLog.append(f"<a> Maximum waiting time at the transfer stop: {self.config['Settings']['maxwaittimetransfer']} min</a>")

        if not self.timetable_mode:
            if self.mode == 1:
                self.textLog.append(f"<a> Start at (hh:mm:ss): {self.config['Settings']['time']}</a>")
            else:
                self.textLog.append(f"<a> Arrive before (hh:mm:ss): {self.config['Settings']['time']}</a>")
        self.textLog.append(f"<a> Maximum travel time: {self.config['Settings']['maxtimetravel']} min</a>")
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append("<a style='font-weight:bold;'>[Aggregation]</a>")
            self.textLog.append(f"<a> Number of bins: {self.config['Settings']['timeinterval']}</a>")

            if self.mode == 2:
                count_features = self.count_layer_destinations
            else:
                count_features = self.count_layer_origins
            self.textLog.append(f'<a> Count: {count_features}</a>')

            if self.config['Settings']['field_ch'] != "":
                print_fields = self.config['Settings']['field_ch']
            else:
                print_fields = "NONE"
            self.textLog.append(f'<a> Aggregated fields: {print_fields}</a>')

        if self.timetable_mode:
            self.textLog.append("<a style='font-weight:bold;'>[Time schedule]</a>")

            if self.mode == 1:
                self.textLog.append(f"<a> Earliest start time: {self.config['Settings']['time']}</a>")
                self.textLog.append(f"<a> Latest start time is T minutes later, T = {self.config['Settings']['maxextratime']} min</a>")
                
            if self.mode == 2:
                self.textLog.append(f"<a> Earliest arrival time: {self.config['Settings']['time']}</a>")
                self.textLog.append(f"<a> Latest arrival time is T minutes later, T = {self.config['Settings']['maxextratime']} min</a>")
                
        self.textLog.append("<a style='font-weight:bold;'>[Visualization]</a>")
        self.textLog.append(f'<a> Visualization layer: {self.layer_visualization_path}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        self.prepareRaptor()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'raptor_area.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://ishusterman.github.io/tutorial/raptor_area.html"
        webbrowser.open(url)

    def showAllLayersInCombo_Point_and_Polygon(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        point_layers = [layer for layer in layers
                        if isinstance(layer, QgsVectorLayer) and
                        (layer.geometryType() == QgsWkbTypes.PointGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry)]
        cmb.clear()
        for layer in point_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo_Polygon(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        polygon_layers = [layer for layer in layers
                          if isinstance(layer, QgsVectorLayer) and
                          layer.geometryType() == QgsWkbTypes.PolygonGeometry and
                          layer.featureCount() > 1]
        cmb.clear()
        for layer in polygon_layers:
            cmb.addItem(layer.name(), [])

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
        else:
            obj.setText(obj.text())

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')
        self.config.read(file_path)

        if 'Layer_field' not in self.config['Settings']:
            self.config['Settings']['Layer_field'] = ''

        if 'LayerDest_field' not in self.config['Settings']:
            self.config['Settings']['LayerDest_field'] = ''

        if 'LayerViz_field' not in self.config['Settings']:
            self.config['Settings']['LayerViz_field'] = ''

        if 'RunOnAir' not in self.config['Settings']:
            self.config['Settings']['RunOnAir'] = 'False'
        
        if 'Admin_time_delta' not in self.config['Settings']:
            self.config['Settings']['Admin_time_delta'] = '900'    

        if 'Admin_iteration' not in self.config['Settings']:
            self.config['Settings']['Admin_iteration'] = '40'        

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToPKL'] = self.txtPathToPKL.text()
        self.config['Settings']['PathToProtocols'] = self.txtPathToProtocols.text()
        self.config['Settings']['Layer'] = self.cmbLayers.currentText()
        self.config['Settings']['Layer_field'] = self.cmbLayers_fields.currentText()
        if hasattr(self, 'cbSelectedOnly1'):
            self.config['Settings']['SelectedOnly1'] = str(
                self.cbSelectedOnly1.isChecked())
        self.config['Settings']['LayerDest'] = self.cmbLayersDest.currentText()
        self.config['Settings']['LayerDest_field'] = self.cmbLayersDest_fields.currentText()

        if hasattr(self, 'cbSelectedOnly2'):
            self.config['Settings']['SelectedOnly2'] = str(
                self.cbSelectedOnly2.isChecked())

        self.config['Settings']['LayerViz'] = self.cmbVizLayers.currentText()
        self.config['Settings']['LayerViz_field'] = self.cmbVizLayers_fields.currentText()

        self.config['Settings']['Min_transfer'] = self.txtMinTransfers.text()
        self.config['Settings']['Max_transfer'] = self.txtMaxTransfers.text()
        self.config['Settings']['MaxExtraTime'] = self.txtMaxExtraTime.text()
        self.config['Settings']['DepartureInterval'] = self.txtDepartureInterval.text()

        self.config['Settings']['MaxWalkDist1'] = self.txtMaxWalkDist1.text()
        self.config['Settings']['MaxWalkDist2'] = self.txtMaxWalkDist2.text()
        self.config['Settings']['MaxWalkDist3'] = self.txtMaxWalkDist3.text()
        self.config['Settings']['TIME'] = self.dtStartTime.dateTime().toString(
            "HH:mm:ss")
        self.config['Settings']['Speed'] = self.txtSpeed.text()
        self.config['Settings']['MaxWaitTime'] = self.txtMaxWaitTime.text()
        self.config['Settings']['MaxWaitTimeTransfer'] = self.txtMaxWaitTimeTransfer.text()
        self.config['Settings']['MaxTimeTravel'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['RunOnAir'] = str(self.cbRunOnAir.isChecked())
        
        with open(f, 'w') as configfile:
            self.config.write(configfile)

        self.aliase = self.txtAliase.text(
        ) if self.txtAliase.text() != "" else self.default_alias

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer'])[0]
        self.layer_origins_path = layer.dataProvider().dataSourceUri().split("|")[
            0]
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest'])[0]
        self.count_layer_origins = layer.featureCount()

        if self.cbSelectedOnly1.isChecked():
            self.count_layer_origins = layer.selectedFeatureCount()
            
      
        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest'])[0]
        self.layer_destinations_path = layer.dataProvider().dataSourceUri().split("|")[
            0]
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer'])[0]
        self.count_layer_destinations = layer.featureCount()

        if self.cbSelectedOnly2.isChecked():
            self.count_layer_destinations = layer.selectedFeatureCount()    

        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerViz'])[0]
        self.layer_visualization_path = layer.dataProvider().dataSourceUri().split("|")[
            0]
        

    def ParametrsShow(self):

        self.readParameters()
        self.txtPathToPKL.setText(self.config['Settings']['PathToPKL'])
        self.txtPathToProtocols.setText(self.config['Settings']['PathToProtocols'])

        
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer'])

        SelectedOnly1 = self.config['Settings']['SelectedOnly1'].lower() == "true"
        self.cbSelectedOnly1.setChecked(SelectedOnly1)

        self.cmbLayersDest.setCurrentText(self.config['Settings']['LayerDest'])

        layer = self.config.get('Settings', 'LayerViz', fallback=None)
        if isinstance(layer, str) and layer.strip():
            self.cmbVizLayers.setCurrentText(layer)

        SelectedOnly2 = self.config['Settings']['SelectedOnly2'].lower() == "true"
        self.cbSelectedOnly2.setChecked(SelectedOnly2)

        self.txtMinTransfers.setText(self.config['Settings']['Min_transfer'])
        self.txtMaxTransfers.setText(self.config['Settings']['Max_transfer'])
        self.txtMaxWalkDist1.setText(self.config['Settings']['MaxWalkDist1'])
        self.txtMaxWalkDist2.setText(self.config['Settings']['MaxWalkDist2'])
        self.txtMaxWalkDist3.setText(self.config['Settings']['MaxWalkDist3'])

        datetime = QDateTime.fromString(
            self.config['Settings']['TIME'], "HH:mm:ss")
        self.dtStartTime.setDateTime(datetime)

        self.txtSpeed.setText(self.config['Settings']['Speed'])
        self.txtMaxWaitTime.setText(self.config['Settings']['MaxWaitTime'])
        self.txtMaxWaitTimeTransfer.setText(self.config['Settings']['MaxWaitTimeTransfer'])
        self.txtMaxTimeTravel.setText(self.config['Settings']['MaxTimeTravel'])
        
        max_extra_time = self.config['Settings'].get('maxextratime', '30')
        self.txtMaxExtraTime.setText(max_extra_time)

        DepartureInterval = self.config['Settings'].get('departureinterval', '5')
        self.txtDepartureInterval.setText(DepartureInterval)

        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field'])
        self.cmbLayersDest_fields.setCurrentText(self.config['Settings']['LayerDest_field'])
        self.cmbVizLayers_fields.setCurrentText(self.config['Settings']['LayerViz_field'])

        RunOnAir = self.config['Settings']['RunOnAir'].lower() == "true"
        self.cbRunOnAir.setChecked(RunOnAir)

        self.txtAliase.setText(self.default_alias)

    def check_folder_and_file(self):

        if not os.path.exists(self.txtPathToPKL.text()):
            self.setMessage(f"Folder '{self.txtPathToPKL.text()}' does not exist")
            return False

        required_files = [  # 'dict_building_vertex.pkl',
            # 'dict_vertex_buildings.pkl',
            # 'graph_footpath.pkl',
            'idx_by_route_stop.pkl',

            'rev_idx_by_route_stop.pkl',
            'routes_by_stop.pkl',
            'routesindx_by_stop.pkl',

            'stops_dict_pkl.pkl',
            'stops_dict_reversed_pkl.pkl',
            'stoptimes_dict_pkl.pkl',

            'stoptimes_dict_reversed_pkl.pkl',
            'transfers_dict_air.pkl',
            'transfers_dict_projection.pkl',

            'graph_projection.pkl',
            'dict_osm_vertex.pkl',
            'dict_vertex_osm.pkl',
            'stop_ids.pkl'
        ]
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToPKL.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in the '{self.txtPathToPKL.text()}' forlder: {missing_files_message}")
            return False
        
        if not os.path.exists(self.txtPathToProtocols.text()):
            self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' does not exist")
            return False

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the '{self.txtPathToProtocols.text()}' folder is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_feature_from_layer(self):
        layer = self.config['Settings']['Layer']
        feature_id_field = self.config['Settings']['Layer_field']
        isChecked = self.cbSelectedOnly1.isChecked()

        if self.mode == 2:
            layer = self.config['Settings']['LayerDest']
            feature_id_field = self.config['Settings']['LayerDest_field']
            isChecked = self.cbSelectedOnly2.isChecked()

        layer = QgsProject.instance().mapLayersByName(layer)[0]
        ids = []
        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')
            return 0

        if isChecked:
            features = layer.selectedFeatures()
            if len(features) == 0:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText(
                    f"'Selected features only' option is chosen but selection set is empty.")
                msgBox.setWindowTitle("Information")
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()
                self.setMessage('')
                return 0

        features = layer.getFeatures()
        if isChecked:
            features = layer.selectedFeatures()

        i = 0
        for feature in features:
            i = + 1
            if i % 50000 == 0:
                QApplication.processEvents()
            id = feature[feature_id_field]
            ids.append((int(id)))

        return ids
   

    def prepareRaptor(self):
        self.break_on = False
        QApplication.processEvents()
        mode = self.mode
        protocol_type = self.protocol_type
        timetable_mode = self.timetable_mode
        
        sources = self.get_feature_from_layer()
        if sources == 0:
            self.run_button.setEnabled(True)
            return 0

        run = True
        if len(sources) > 10:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            take_min = round((len(sources)*2)/60)
            msgBox.setText(
                f"Layer contains {len(sources)} feature and it will take at least {take_min} minutes to finish the computations. Maximum 10 feature are recommended. Are you sure?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.Yes:
                run = True
            else:
                run = False

        if run:
            PathToNetwork = self.config['Settings']['PathToPKL']
            raptor_mode = mode
            exlude_routes = False
            numbers_routes = None
            route_dict = None
            RunOnAir = self.config['Settings']['RunOnAir'] == 'True'

            Layer = self.config['Settings']['Layer']
            LayerDest = self.config['Settings']['LayerDest']

            if self.mode == 2:
                Layer = self.config['Settings']['LayerDest']
                LayerDest = self.config['Settings']['Layer']

            layer_origin = QgsProject.instance().mapLayersByName(Layer)[0]
            layer_dest = QgsProject.instance().mapLayersByName(LayerDest)[0]    
            MaxWalkDist1 = int(self.config['Settings']['MaxWalkDist1'])
            layer_dest_field = self.config['Settings']['LayerDest_field']

            if self.mode == 2:
                layer_dest_field = self.config['Settings']['Layer_field']

            Speed = float(self.config['Settings']['Speed'].replace(',', '.')) * 1000 / 3600  # from km/h to m/sec

            
            if not os.path.exists(self.folder_name):
                os.makedirs(self.folder_name)
            else:
                self.setMessage(f"Folder '{self.folder_name}' already exists")
                self.run_button.setEnabled(True)
                self.close_button.setEnabled(True)
                self.textLog.clear()
                self.tabWidget.setCurrentIndex(0)
                self.progressBar.setValue(0)
                return 0
            

            dictionary, dictionary2 = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        exlude_routes,
                        numbers_routes,
                        route_dict,
                        RunOnAir,

                        layer_origin,
                        layer_dest,
                        MaxWalkDist1,
                        layer_dest_field,
                        Speed
                        )
            
            if self.shift_mode:
                START_TIME = time_to_seconds(self.config['Settings']['TIME'])
                time_delta = int(self.config['Settings']['Admin_time_delta'])
                if 'admin_t_f' in self.config['Settings']:
                    Tf = time_to_seconds(self.config['Settings']['admin_t_f'])
                else:
                    Tf = time_to_seconds("20:00:00")
                
                self.folder_name_copy = os.path.join(self.folder_name)
                print (self.folder_name_copy)
                os.makedirs(self.folder_name_copy, exist_ok=True)
                
                i = 0
                while True:
                    D_TIME = START_TIME + i * time_delta 
                
                    if D_TIME > Tf:
                            break 
                                        
                    D_TIME_str = seconds_to_time(D_TIME)
                    if not self.timetable_mode:
                        if self.mode == 1:
                            self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                        else:
                            self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                    if self.timetable_mode:
                       if self.mode == 1:
                           self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                       else:
                           self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                
                 
                    postfix = i + 1 
                    self.folder_name = os.path.join(self.folder_name_copy, f'{self.txtAliase.text()}-{postfix}')
                    os.makedirs(self.folder_name, exist_ok=True)
        
                    runRaptorWithProtocol(self,
                                  sources,
                                  mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  self.aliase,
                                  dictionary,
                                  dictionary2,
                                  self.shift_mode
                                  )
                    i += 1
                    
                    if self.break_on:
                        self.setMessage("Statistic computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">Statistic computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                    
                base_path = self.folder_name_copy
                output_path = os.path.join(base_path, f"stat_{self.aliase}.csv")
                processor = DayStat_DestinationID(base_path, output_path)
                processor.process_files()
                self.textLog.append(f'<a href="file:///{self.txtPathToProtocols.text()}" target="_blank" >Statistics in folder</a>')

            if self.shift_ctrl_mode:
                if  os.path.exists(f'{self.folder_name}_from'):  
                    self.setMessage(f"Folder '{f'{self.folder_name}_from'}' already exists")
                    self.run_button.setEnabled(True)
                    self.close_button.setEnabled(True)
                    self.textLog.clear()
                    self.tabWidget.setCurrentIndex(0)
                    self.progressBar.setValue(0)
                    self.shift_ctrl_mode = False
                    return 0
                
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating from-to accessibility</a>")
                ###########################
                #  From
                # #########################
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating from accessibility</a>")
                START_TIME = time_to_seconds(self.config['Settings']['TIME'])
                time_delta = int(self.config['Settings']['Admin_time_delta'])
                                
                if 'admin_t_f' in self.config['Settings']:
                    Tf = time_to_seconds(self.config['Settings']['admin_t_f'])
                else:
                    Tf = time_to_seconds("20:00:00")
                
                self.folder_name_from = f'{self.folder_name}_from'
                os.makedirs(self.folder_name_from, exist_ok=True)

                i = 0
                
                while True:
                
                    D_TIME = START_TIME + i * time_delta 
                    if D_TIME > Tf:
                            break 

                    D_TIME_str = seconds_to_time(D_TIME)
                    if self.timetable_mode:
                        self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                    else:
                        self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                 
                    postfix = i + 1
                    self.folder_name = os.path.join(self.folder_name_from, str(postfix)) 
                    os.makedirs(self.folder_name, exist_ok=True)
                    runRaptorWithProtocol(self,
                                  sources,
                                  mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  self.aliase,
                                  dictionary,
                                  dictionary2,
                                  self.shift_ctrl_mode
                                  )
                    if self.break_on:
                        self.setMessage("From-to accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">From-to accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                    i += 1
                
                ###########################
                #  TO
                # #########################
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating to accessibility</a>")
                
                self.mode = 2
                raptor_mode = 2    
                
                dictionary, dictionary2 = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        exlude_routes,
                        numbers_routes,
                        route_dict,
                        RunOnAir,

                        layer_origin,
                        layer_dest,
                        MaxWalkDist1,
                        layer_dest_field,
                        Speed
                        )
                                
                self.folder_name = f'{self.txtPathToProtocols.text()}//{self.txtAliase.text()}'

                self.folder_name_to = f'{self.folder_name}_to'
                os.makedirs(self.folder_name_to, exist_ok=True)

                i = 0

                while True:
                    D_TIME = START_TIME + i * time_delta 
                    if D_TIME > Tf:
                            break
                   
                    D_TIME_str = seconds_to_time(D_TIME)
                                           
                    if self.timetable_mode:
                       self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                    else:   
                       self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                    
                    postfix = i + 1
                    self.folder_name = os.path.join(self.folder_name_to, str(postfix)) 
                    os.makedirs(self.folder_name, exist_ok=True)
                                        
                    runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  self.aliase,
                                  dictionary,
                                  dictionary2,
                                  self.shift_ctrl_mode
                                  )
                    i += 1
                    if self.break_on:
                        self.setMessage("From-to accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">From-to accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                if not(self.break_on):

                    processor = StatFromTo(self,
                                           self.folder_name_from, 
                                           self.folder_name_to, 
                                           self.txtPathToProtocols.text(), 
                                           self.aliase,                                    
                                           timetable_mode
                                           )
                    processor.process_files()
                    self.textLog.append(f'<a href="file:///{self.txtPathToProtocols.text()}" target="_blank" >Statistics in folder</a>')

            if not(self.shift_mode) and not (self.shift_ctrl_mode):
                
                self.run_button.setEnabled(False)
                D_TIME = time_to_seconds(self.config['Settings']['TIME'])
                runRaptorWithProtocol(self,
                                  sources,
                                  mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  self.aliase,
                                  dictionary,
                                  dictionary2
                                  )
            """
         _, self.folder_name = self.profile_runRaptorWithProtocol( 
                                                  sources, 
                                                  mode, 
                                                  protocol_type, 
                                                  timetable_mode,                                                   
                                                  )
         """
            return 1

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")
            return 0
    """
    def profile_runRaptorWithProtocol(self,
                                      sources,
                                      mode,
                                      protocol_type,
                                      timetable_mode):
        pr = cProfile.Profile()
        pr.enable()

        result = runRaptorWithProtocol(self, sources, mode, protocol_type, timetable_mode,
                                       self.cbSelectedOnly1.isChecked(), self.cbSelectedOnly2.isChecked())

        pr.disable()

        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.dump_stats(
            r"C:/temp/plugin_profile.txt")

        return result
    """
    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
