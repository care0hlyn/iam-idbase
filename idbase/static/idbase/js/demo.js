// javascript file for demo purposes only
var app = angular.module('identityApp');

app.controller('MakeErrorCtrl', ['ErrorSvc', function(ErrorSvc){
    this.doIt = function() {
        ErrorSvc.state.isErrorSet = true;
    };
}]);