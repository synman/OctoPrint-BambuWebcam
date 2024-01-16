$(function () {
    function BambuWebcamWizardViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.onWizardFinish = function () {
            if (self.settingsViewModel.streamUrl()) {
                return "reload";
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: BambuWebcamWizardViewModel,
        dependencies: ["BambuWebcamSettingsViewModel"],
        elements: ["#wizard_bambuwebcam"]
    });
});
