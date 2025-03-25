#ifndef CONTROL_APP_H
#define CONTROL_APP_H

#include <QMainWindow>
#include <QPushButton>
#include <QLabel>
#include <QLineEdit>
#include <QTimer>
#include <vector>
#include <string>

struct Backend {
    std::string host;
    std::vector<int> ports;
    std::string name;
    bool ready;
    std::vector<int> sockets;  // socket file descriptors
};

class ControlApp : public QMainWindow {
    Q_OBJECT

public:
    ControlApp(QWidget *parent = nullptr);
    ~ControlApp();

protected:
    void closeEvent(QCloseEvent *event) override;

private slots:
    void connectToServer();
    void applyConfiguration();
    void toggleAction();
    void sendEvent();
    void enableEventButton();

private:
    void setupUI();
    void centerWindow();
    std::pair<bool, std::vector<std::string>> sendTcpMessage(const std::string& message);
    
    std::vector<Backend> backends;
    std::vector<QLineEdit*> ipInputs;
    std::vector<QLabel*> statusLabels;
    
    QPushButton* toggleBtn;
    QPushButton* eventBtn;
    QPushButton* applyBtn;
    
    QTimer* timer;
    QTimer* statusTimer;
    
    bool isToggleOn;
    bool eventSent;
};

#endif // CONTROL_APP_H 