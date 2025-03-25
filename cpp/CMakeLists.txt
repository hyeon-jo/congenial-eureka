cmake_minimum_required(VERSION 3.1.0)

project(control_app)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt5 COMPONENTS Widgets REQUIRED)

add_executable(control_app
    main.cpp
    control_app.cpp
    control_app.h
)

target_link_libraries(control_app PRIVATE Qt5::Widgets) 