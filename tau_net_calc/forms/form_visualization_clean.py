import os
import webbrowser
import configparser
from time import sleep
from datetime import datetime

from qgis.PyQt import QtCore

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QRegExp,
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )

from PyQt5.QtGui import (QRegExpValidator,
                        QDesktopServices)

from PyQt5 import uic

from common import get_qgis_info, check_file_parameters_accessibility
from visualization_clean import cls_clean_visualization

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'visualization_clean.ui')
)    

class form_visualization_clean(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.label.setText("Folder to store layers for visualization")
        self.label_3.setText("Layer of buildings")

        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])
        
        fix_size = 13 * self.txtAddHex.fontMetrics().width('x')
        self.txtAddHex.setFixedWidth(fix_size)

        #  create a regular expression instance for integers
        regex1 = QRegExp(r"0|[1-9]\d{0,3}|10000")
        int_validator1 = QRegExpValidator(regex1)
        self.txtAddHex.setValidator(int_validator1)

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setMaximum(5)
        self.progressBar.setValue(0)

        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog ())

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.showAllLayersInCombo(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)
        
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

        self.task = None
        self.already_show_info = False

        self.show()
        self.ParametrsShow()

    def get_layer_buildings(self):
        selected_item = self.cmbLayers.currentText()
        if os.path.isfile(selected_item):
            layer_building = QgsVectorLayer(selected_item, "LayerBuildings", "ogr")
        else:
            layers = QgsProject.instance().mapLayersByName(selected_item)
            if layers:  
                layer_building = layers[0]
            else:
                layer_building = None  
        return layer_building
    
    def open_file_dialog(self):
        
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose a File",
            "",
            "Shapefile (*.shp);"
        )

        if file_path:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.cmbLayers.addItem(file_path, file_path)
                index = self.cmbLayers.findText(file_path)
                self.cmbLayers.setCurrentIndex(index)

    def showAllLayersInCombo(self, cmb, geometry_type=QgsWkbTypes.PolygonGeometry):
        """
        Populates a combobox with layers of a specified geometry type.

        :param cmb: QComboBox to populate
        :param geometry_type: Geometry type to filter layers (default: PolygonGeometry)
        """
        layers = QgsProject.instance().mapLayers().values()
        filtered_layers = [
            layer for layer in layers
            if isinstance(layer, QgsVectorLayer) and
            layer.geometryType() == geometry_type and
            not layer.name().startswith("Temp") and
            'memory' not in layer.dataProvider().dataSourceUri()
        ]
        cmb.clear()
        for layer in filtered_layers:
            cmb.addItem(layer.name(), [])


    def EnableComboBox(self, state):

        if state == QtCore.Qt.Checked:
            self.cmbFields.setEnabled(True)
        else:
            self.cmbFields.setEnabled(False)
    
    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
        else:
            obj.setText(obj.text())

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        if self.task:
            self.task.cancel() 
            self.progressBar.setValue(0) 
            if not (self.already_show_info):
                self.textLog.append(f'<a><b><font color="red">Process is interrupted by user</font> </b></a>')
                self.already_show_info = True
            self.setMessage("")

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        self.layer_buildings  = self.get_layer_buildings()
        self.layer_buildings_path = self.layer_buildings.dataProvider().dataSourceUri().split("|")[
            0]
        
        if not (self.check_type_layer_buildings()):
            self.run_button.setEnabled(True)
            return 0

        self.saveParameters()
        self.readParameters()

        self.setMessage("Build visualizalization layers ...")
        self.folder_name = f'{self.txtPathToProtocols.text()}'
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

        #self.layer_buildings = QgsProject.instance().mapLayersByName(
        #    self.config['Settings']['layer_clean-visualization'])[0]
        
        self.add_hex = self.config['Settings']['AddHex_clean-visualization']
        self.textLog.append(f"<a>Layer of buildings: {self.layer_buildings_path}</a>")
        self.textLog.append(f"<a>Add a hexagons layer with a side length: {self.add_hex}m</a>")        
        self.folder_name = self.config['Settings']['PathToProtocols_clean-visualization']
        self.textLog.append(f"<a>Folder to store layers for visualization: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False

        self.task = cls_clean_visualization(
            self, begin_computation_time, self.layer_buildings, self.folder_name)
        QgsApplication.taskManager().addTask(self.task)
        sleep(1)
        QApplication.processEvents()

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'building_pkl.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://ishusterman.github.io/tutorial/building_pkl.html"
        webbrowser.open(url)

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'layer_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['layer_clean-visualization'] = ''

        if 'PathToProtocols_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_clean-visualization'] = 'C:/'

        if 'AddHex_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['AddHex_clean-visualization'] = ''    

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['Layer_clean-visualization'] = self.cmbLayers.currentText()
        self.config['Settings']['PathToProtocols_clean-visualization'] = self.txtPathToProtocols.text()
        self.config['Settings']['AddHex_clean-visualization'] = self.txtAddHex.text()
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):
        self.readParameters()

        if os.path.isfile(self.config['Settings']['Layer_clean-visualization']):
            self.cmbLayers.addItem(self.config['Settings']['Layer_clean-visualization'])
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_clean-visualization'])
        
        self.txtPathToProtocols.setText(self.config['Settings']['PathToProtocols_clean-visualization'])
        self.txtAddHex.setText(self.config['Settings']['AddHex_clean-visualization'])

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_type_layer_buildings(self):
        
        layer = self.layer_buildings

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f"Layer '{self.cmbLayers.currentText()}' is empty")
            return 0

        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break
        
        if not (feature_geometry_type in {QgsWkbTypes.PolygonGeometry}):
            self.setMessage(f"Features in the layer '{self.cmbLayers.currentText()}' must be polygones")
            return 0

        return 1

    def check_folder_and_file(self):

        if not os.path.exists(self.txtPathToProtocols.text()):
            self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' does not exist")
            return False

        """
        # check for the presence of .shp files in the folder
        if os.path.isdir(self.txtPathToProtocols.text()):
            for file in os.listdir(self.txtPathToProtocols.text()):
                if file.lower().endswith('.shp'):
                    self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' is not empty")
                    return False
        """

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False

        return True

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)