#include "control_app.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setStyle("Fusion");
    
    ControlApp window;
    window.show();
    
    return app.exec();
} 