#include "control_app.h"
#include <QVBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QMessageBox>
#include <QApplication>
#include <QScreen>
#include <QCloseEvent>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <ctime>
#include <chrono>
#include <iostream>

// 시스템 함수와 Qt 함수의 충돌을 피하기 위한 네임스페이스 사용
namespace sys {
    using ::close;
    using ::connect;
}

ControlApp::ControlApp(QWidget *parent)
    : QMainWindow(parent), isToggleOn(false), eventSent(false)
{
    setWindowTitle("Control Panel");
    
    // Initialize backends
    backends = {
        {
            "localhost",
            {9090, 9091},
            "Backend 1",
            false,
            {-1, -1}
        },
        {
            "localhost",
            {9092, 9093},
            "Backend 2",
            false,
            {-1, -1}
        }
    };
    
    setupUI();
    
    // Setup timers
    timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, &ControlApp::enableEventButton);
    
    statusTimer = new QTimer(this);
    connect(statusTimer, &QTimer::timeout, this, &ControlApp::connectToServer);
    statusTimer->start(1000);  // Check every 1 second
    
    eventBtn->setEnabled(true);
}

ControlApp::~ControlApp()
{
    // Clean up sockets
    for (auto& backend : backends) {
        for (int sock : backend.sockets) {
            if (sock != -1) {
                sys::close(sock);
            }
        }
    }
}

void ControlApp::setupUI()
{
    QWidget* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);
    QVBoxLayout* mainLayout = new QVBoxLayout(centralWidget);
    mainLayout->setSpacing(20);
    
    // Config group
    QGroupBox* configGroup = new QGroupBox("Backend Configuration", this);
    QGridLayout* configLayout = new QGridLayout;
    configLayout->setSpacing(10);
    
    for (size_t i = 0; i < backends.size(); ++i) {
        QLabel* ipLabel = new QLabel(QString::fromStdString(backends[i].name + " IP:"), this);
        ipLabel->setStyleSheet("font-size: 32px;");
        
        QLineEdit* ipInput = new QLineEdit(QString::fromStdString(backends[i].host), this);
        ipInput->setPlaceholderText("Enter IP address");
        ipInput->setStyleSheet("font-size: 32px; padding: 5px;");
        
        configLayout->addWidget(ipLabel, i, 0);
        configLayout->addWidget(ipInput, i, 1);
        ipInputs.push_back(ipInput);
        
        QString portText = QString("Ports: %1, %2")
            .arg(backends[i].ports[0])
            .arg(backends[i].ports[1]);
        QLabel* portLabel = new QLabel(portText, this);
        portLabel->setStyleSheet("font-size: 32px;");
        configLayout->addWidget(portLabel, i, 2);
    }
    
    applyBtn = new QPushButton("Apply Configuration", this);
    applyBtn->setMinimumSize(200, 50);
    applyBtn->setStyleSheet(
        "QPushButton {"
        "   font-size: 32px;"
        "   font-weight: bold;"
        "   padding: 5px;"
        "   background-color: #008CBA;"
        "   color: white;"
        "   border-radius: 5px;"
        "}"
        "QPushButton:hover {"
        "   background-color: #007399;"
        "}"
    );
    connect(applyBtn, &QPushButton::clicked, this, &ControlApp::applyConfiguration);
    configLayout->addWidget(applyBtn, backends.size(), 0, 1, 4);
    
    configGroup->setLayout(configLayout);
    mainLayout->addWidget(configGroup);
    
    // Control panel
    QGroupBox* controlGroup = new QGroupBox("Control Panel", this);
    QGridLayout* controlLayout = new QGridLayout;
    
    for (size_t i = 0; i < backends.size(); ++i) {
        QLabel* label = new QLabel(QString::fromStdString(backends[i].name + ": Not Connected"), this);
        label->setStyleSheet("color: red; font-size: 32px;");
        controlLayout->addWidget(label, 0, i, Qt::AlignCenter);
        statusLabels.push_back(label);
    }
    
    toggleBtn = new QPushButton("Start", this);
    toggleBtn->setMinimumSize(200, 50);
    toggleBtn->setStyleSheet(
        "QPushButton {"
        "   font-size: 32px;"
        "   font-weight: bold;"
        "   padding: 5px;"
        "   background-color: #4CAF50;"
        "   color: white;"
        "   border-radius: 5px;"
        "}"
        "QPushButton:hover {"
        "   background-color: #45a049;"
        "}"
    );
    
    eventBtn = new QPushButton("Send Event", this);
    eventBtn->setMinimumSize(200, 50);
    eventBtn->setStyleSheet(
        "QPushButton {"
        "   font-size: 32px;"
        "   font-weight: bold;"
        "   padding: 5px;"
        "   background-color: #008CBA;"
        "   color: white;"
        "   border-radius: 5px;"
        "}"
        "QPushButton:hover {"
        "   background-color: #007399;"
        "}"
        "QPushButton:disabled {"
        "   background-color: #cccccc;"
        "   color: #666666;"
        "}"
    );
    
    connect(toggleBtn, &QPushButton::clicked, this, &ControlApp::toggleAction);
    connect(eventBtn, &QPushButton::clicked, this, &ControlApp::sendEvent);
    
    controlLayout->addWidget(toggleBtn, 1, 0, 1, 2, Qt::AlignCenter);
    controlLayout->addWidget(eventBtn, 2, 0, 1, 2, Qt::AlignCenter);
    
    controlGroup->setLayout(controlLayout);
    mainLayout->addWidget(controlGroup);
    
    setMinimumSize(1200, 800);
    resize(1200, 800);
    centerWindow();
    
    setStyleSheet(
        "QGroupBox {"
        "   font-size: 32px;"
        "   font-weight: bold;"
        "   margin-top: 1ex;"
        "}"
        "QGroupBox::title {"
        "   subcontrol-origin: margin;"
        "   subcontrol-position: top center;"
        "   padding: 0 3px;"
        "}"
        "QLineEdit {"
        "   padding: 5px;"
        "   border: 1px solid #999;"
        "   border-radius: 3px;"
        "}"
    );
}

void ControlApp::connectToServer()
{
    bool allConnected = true;
    
    for (size_t i = 0; i < backends.size(); ++i) {
        auto& backend = backends[i];
        
        // First message exchange (1 -> 2)
        for (size_t j = 0; j < backend.ports.size(); ++j) {
            if (backend.sockets[j] != -1) continue;
            
            try {
                int sock = socket(AF_INET, SOCK_STREAM, 0);
                if (sock == -1) {
                    throw std::runtime_error("Socket creation failed");
                }
                
                struct timeval tv;
                tv.tv_sec = 0;
                tv.tv_usec = 500000;  // 0.5 seconds
                setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
                
                struct sockaddr_in serverAddr;
                serverAddr.sin_family = AF_INET;
                serverAddr.sin_port = htons(backend.ports[j]);
                serverAddr.sin_addr.s_addr = inet_addr(backend.host.c_str());
                
                if (sys::connect(sock, (struct sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
                    sys::close(sock);
                    throw std::runtime_error("Connection failed");
                }
                
                // Send first message and receive response
                // TODO: Implement protocol header message exchange
                
                backend.sockets[j] = sock;
                
            } catch (const std::exception& e) {
                std::cerr << "Error with " << backend.name << ":" << backend.ports[j] 
                         << ": " << e.what() << std::endl;
                allConnected = false;
                statusLabels[i]->setText(QString::fromStdString(backend.name + ": Not Connected"));
                statusLabels[i]->setStyleSheet("color: red; font-size: 32px;");
                continue;
            }
        }
        
        // Second message exchange (3 -> 4)
        if (std::all_of(backend.sockets.begin(), backend.sockets.end(), 
                       [](int sock) { return sock != -1; })) {
            try {
                for (size_t j = 0; j < backend.ports.size(); ++j) {
                    // TODO: Implement second message exchange
                }
                
                backend.ready = true;
                statusLabels[i]->setText(QString::fromStdString(backend.name + ": Connected"));
                statusLabels[i]->setStyleSheet("color: green; font-size: 32px;");
                
            } catch (const std::exception& e) {
                std::cerr << "Error with " << backend.name << " second message exchange: " 
                         << e.what() << std::endl;
                allConnected = false;
                statusLabels[i]->setText(QString::fromStdString(backend.name + ": Not Connected"));
                statusLabels[i]->setStyleSheet("color: red; font-size: 32px;");
                
                for (int sock : backend.sockets) {
                    if (sock != -1) sys::close(sock);
                }
                std::fill(backend.sockets.begin(), backend.sockets.end(), -1);
            }
        }
    }
    
    if (allConnected && std::all_of(backends.begin(), backends.end(), 
                                   [](const Backend& b) { return b.ready; })) {
        statusTimer->stop();
        eventSent = false;
        eventBtn->setEnabled(true);
        toggleBtn->setEnabled(true);
        std::cout << "All backends connected successfully" << std::endl;
    }
}

void ControlApp::applyConfiguration()
{
    for (size_t i = 0; i < backends.size(); ++i) {
        QString ip = ipInputs[i]->text().trimmed();
        if (ip.isEmpty()) {
            QMessageBox::warning(this, "Configuration Error", 
                               QString::fromStdString(backends[i].name + ": IP address cannot be empty"));
            return;
        }
        backends[i].host = ip.toStdString();
    }
    QMessageBox::information(this, "Success", "Configuration applied successfully");
}

void ControlApp::centerWindow()
{
    QScreen* screen = QGuiApplication::primaryScreen();
    QRect screenGeometry = screen->geometry();
    int x = (screenGeometry.width() - width()) / 2;
    int y = (screenGeometry.height() - height()) / 2;
    move(x, y);
}

void ControlApp::toggleAction()
{
    if (!isToggleOn) {
        auto [success, failedBackends] = sendTcpMessage("START");
        if (success) {
            toggleBtn->setText("End");
            toggleBtn->setStyleSheet(
                "QPushButton {"
                "   font-size: 32px;"
                "   font-weight: bold;"
                "   padding: 5px;"
                "   background-color: #ff9999;"
                "   color: white;"
                "   border-radius: 5px;"
                "}"
                "QPushButton:hover {"
                "   background-color: #ff8080;"
                "}"
            );
            isToggleOn = true;
            eventBtn->setEnabled(false);
        } else {
            if (!failedBackends.empty()) {
                std::string failureMessage = "CONNECTION_FAIL:";
                for (const auto& name : failedBackends) {
                    failureMessage += name + ",";
                }
                failureMessage.pop_back();  // Remove last comma
                sendTcpMessage(failureMessage);
            }
            toggleBtn->setText("Start");
            toggleBtn->setStyleSheet(
                "QPushButton {"
                "   font-size: 32px;"
                "   font-weight: bold;"
                "   padding: 5px;"
                "   background-color: #4CAF50;"
                "   color: white;"
                "   border-radius: 5px;"
                "}"
                "QPushButton:hover {"
                "   background-color: #45a049;"
                "}"
            );
            isToggleOn = false;
            eventBtn->setEnabled(true);
        }
    } else {
        auto [success, _] = sendTcpMessage("END");
        if (success) {
            toggleBtn->setText("Start");
            toggleBtn->setStyleSheet(
                "QPushButton {"
                "   font-size: 32px;"
                "   font-weight: bold;"
                "   padding: 5px;"
                "   background-color: #4CAF50;"
                "   color: white;"
                "   border-radius: 5px;"
                "}"
                "QPushButton:hover {"
                "   background-color: #45a049;"
                "}"
            );
            isToggleOn = false;
            eventBtn->setEnabled(true);
        }
    }
}

void ControlApp::sendEvent()
{
    // TODO: Implement event sending logic
}

void ControlApp::enableEventButton()
{
    eventBtn->setEnabled(true);
    timer->stop();
}

void ControlApp::closeEvent(QCloseEvent *event)
{
    for (auto& backend : backends) {
        for (int sock : backend.sockets) {
            if (sock != -1) {
                sys::close(sock);
            }
        }
    }
    event->accept();
}

std::pair<bool, std::vector<std::string>> ControlApp::sendTcpMessage(const std::string& message)
{
    // TODO: Implement TCP message sending logic
    return {true, {}};
} 