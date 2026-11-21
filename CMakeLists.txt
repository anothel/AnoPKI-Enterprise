# SPDX-License-Identifier: MPL-2.0

cmake_minimum_required(VERSION 3.20)

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" ANOPKI_VERSION)
string(STRIP "${ANOPKI_VERSION}" ANOPKI_VERSION)
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" ANOPKI_PROJECT_VERSION "${ANOPKI_VERSION}")

project(anopki VERSION ${ANOPKI_PROJECT_VERSION} LANGUAGES CXX)

set(ANOPKI_PRODUCT_PROFILE "enterprise-openssl" CACHE STRING "AnoPKI Enterprise product profile")
set_property(CACHE ANOPKI_PRODUCT_PROFILE PROPERTY STRINGS enterprise-openssl enterprise-anocrypto-c)
set(ANOCRYPTO_SDK_ROOT "" CACHE PATH "Installed AnoCrypto-C SDK prefix")
option(ANOPKI_ENABLE_FUZZING "Build local libFuzzer parser targets" OFF)
option(ANOPKI_ENTERPRISE_EDITION "Build Enterprise edition overlay metadata" ON)

if(NOT ANOPKI_ENTERPRISE_EDITION)
    message(FATAL_ERROR "The Enterprise repository requires ANOPKI_ENTERPRISE_EDITION=ON")
endif()

if(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl")
    set(ANOPKI_SELECTED_BACKEND_ID "openssl")
    set(ANOPKI_PROFILE_REQUIRES_FULL_OPERATIONS 1)
    find_package(OpenSSL REQUIRED COMPONENTS Crypto)
    set(ANOPKI_OPENSSL_BACKEND_ABI_VERSION 1)
    set(ANOPKI_ANOCRYPTO_PROFILE 0)
    if(DEFINED OpenSSL_VERSION)
        set(ANOPKI_OPENSSL_CONFIG_VERSION "${OpenSSL_VERSION}")
    elseif(DEFINED OPENSSL_VERSION)
        set(ANOPKI_OPENSSL_CONFIG_VERSION "${OPENSSL_VERSION}")
    else()
        set(ANOPKI_OPENSSL_CONFIG_VERSION "unknown")
    endif()
    set(ANOPKI_OPENSSL_BACKEND_FINGERPRINT_INPUT
        "profile=${ANOPKI_PRODUCT_PROFILE}|edition=enterprise|backend=openssl|abi=${ANOPKI_OPENSSL_BACKEND_ABI_VERSION}|anopki=${ANOPKI_VERSION}|compiler=${CMAKE_CXX_COMPILER_ID}-${CMAKE_CXX_COMPILER_VERSION}|openssl=${ANOPKI_OPENSSL_CONFIG_VERSION}"
    )
    string(SHA256 ANOPKI_OPENSSL_BACKEND_BUILD_FINGERPRINT_HASH "${ANOPKI_OPENSSL_BACKEND_FINGERPRINT_INPUT}")
    set(ANOPKI_OPENSSL_BACKEND_BUILD_FINGERPRINT "sha256:${ANOPKI_OPENSSL_BACKEND_BUILD_FINGERPRINT_HASH}")
    configure_file(
        src/backends/openssl/openssl_backend_config.hpp.in
        generated/anopki/openssl_backend_config.hpp
        @ONLY
    )
elseif(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-anocrypto-c")
    set(ANOPKI_SELECTED_BACKEND_ID "anocrypto-c")
    set(ANOPKI_PROFILE_REQUIRES_FULL_OPERATIONS 1)
    set(ANOPKI_ANOCRYPTO_PROFILE 1)
    if(ANOCRYPTO_SDK_ROOT)
        list(PREPEND CMAKE_PREFIX_PATH "${ANOCRYPTO_SDK_ROOT}")
    endif()
    find_package(AnoCryptoC 0.1.0 EXACT CONFIG REQUIRED)
else()
    message(FATAL_ERROR "Unsupported ANOPKI_PRODUCT_PROFILE: ${ANOPKI_PRODUCT_PROFILE}")
endif()

add_library(anopki_core
    src/core/backend.cpp
    src/core/crl.cpp
    src/core/csr.cpp
    src/core/issue.cpp
    src/core/ocsp.cpp
    src/core/runtime.cpp
    src/version.cpp
    src/enterprise/edition.cpp
)
add_library(anopki::core ALIAS anopki_core)

configure_file(
    src/version_config.hpp.in
    generated/anopki/version_config.hpp
    @ONLY
)

target_compile_features(anopki_core PUBLIC cxx_std_20)
if(MSVC)
    target_compile_options(anopki_core PUBLIC /EHsc)
endif()
target_include_directories(anopki_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/generated
)
target_compile_definitions(anopki_core
    PUBLIC ANOPKI_ENTERPRISE_EDITION=1
    PRIVATE
        ANOPKI_PRODUCT_PROFILE_ID="${ANOPKI_PRODUCT_PROFILE}"
        ANOPKI_EDITION_ID="enterprise"
        ANOPKI_SELECTED_BACKEND_ID="${ANOPKI_SELECTED_BACKEND_ID}"
        ANOPKI_PROFILE_REQUIRES_FULL_OPERATIONS=${ANOPKI_PROFILE_REQUIRES_FULL_OPERATIONS}
        ANOPKI_ANOCRYPTO_PROFILE=${ANOPKI_ANOCRYPTO_PROFILE}
)

if(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl")
    add_library(anopki_openssl_adapter
        src/backends/openssl/crl.cpp
        src/backends/openssl/csr.cpp
        src/backends/openssl/issue.cpp
        src/backends/openssl/key_providers/file_key_provider.cpp
        src/backends/openssl/key_providers/provider_resolver.cpp
        src/backends/openssl/ocsp.cpp
        src/backends/openssl/openssl_backend.cpp
    )
    add_library(anopki::openssl_adapter ALIAS anopki_openssl_adapter)
    target_compile_features(anopki_openssl_adapter PUBLIC cxx_std_20)
    if(MSVC)
        target_compile_options(anopki_openssl_adapter PUBLIC /EHsc)
    endif()
    target_include_directories(anopki_openssl_adapter PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/src/backends/openssl
        ${CMAKE_CURRENT_BINARY_DIR}/generated
    )
    target_link_libraries(anopki_openssl_adapter PRIVATE OpenSSL::Crypto)
    set(ANOPKI_SELECTED_ADAPTER_TARGET anopki::openssl_adapter)
else()
    add_library(anopki_enterprise_anocrypto_adapter STATIC
        src/backends/anocrypto_c/anocrypto_backend.cpp
        src/backends/anocrypto_c/pki.cpp
    )
    target_compile_features(anopki_enterprise_anocrypto_adapter PUBLIC cxx_std_20)
    target_include_directories(anopki_enterprise_anocrypto_adapter PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    )
    target_link_libraries(anopki_enterprise_anocrypto_adapter
        PUBLIC anopki::core
        PRIVATE AnoCryptoC::AnoCryptoC
    )
    function(anopki_stage_anocrypto_runtime target)
        if(WIN32)
            add_custom_command(
                TARGET ${target} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    $<TARGET_FILE:AnoCryptoC::AnoCryptoC>
                    $<TARGET_FILE_DIR:${target}>
            )
        endif()
    endfunction()
    set(ANOPKI_SELECTED_ADAPTER_TARGET anopki_enterprise_anocrypto_adapter)
endif()

add_executable(anopki-core src/cli/main.cpp)
target_link_libraries(anopki-core PRIVATE anopki::core ${ANOPKI_SELECTED_ADAPTER_TARGET})
if(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-anocrypto-c")
    anopki_stage_anocrypto_runtime(anopki-core)
endif()

if(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl")
    add_custom_target(anopki-enterprise-openssl DEPENDS anopki-core)
else()
    add_custom_target(anopki-enterprise-anocrypto-c DEPENDS anopki-core)
endif()

if(WIN32 AND ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl" AND OPENSSL_ROOT_DIR)
    file(TO_CMAKE_PATH "${OPENSSL_ROOT_DIR}" OPENSSL_ROOT_DIR_CMAKE)
    file(GLOB OPENSSL_RUNTIME_DLLS CONFIGURE_DEPENDS "${OPENSSL_ROOT_DIR_CMAKE}/bin/*.dll")
    if(OPENSSL_RUNTIME_DLLS)
        add_custom_command(
            TARGET anopki-core POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different ${OPENSSL_RUNTIME_DLLS} $<TARGET_FILE_DIR:anopki-core>
            COMMAND_EXPAND_LISTS
        )
    endif()
endif()

if(ANOPKI_ENABLE_FUZZING)
    if(NOT ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl")
        message(FATAL_ERROR "Parser fuzzing currently requires ANOPKI_PRODUCT_PROFILE=enterprise-openssl")
    endif()
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        message(FATAL_ERROR "ANOPKI_ENABLE_FUZZING requires Clang with libFuzzer support")
    endif()
    function(add_anopki_parser_fuzzer target compile_definition)
        add_executable(${target} tests/fuzz/core_parser_fuzz.cpp)
        target_compile_definitions(${target} PRIVATE ${compile_definition})
        target_compile_options(${target} PRIVATE -fsanitize=fuzzer,address)
        target_link_options(${target} PRIVATE -fsanitize=fuzzer,address)
        target_link_libraries(${target} PRIVATE anopki::core anopki::openssl_adapter)
    endfunction()
    add_anopki_parser_fuzzer(anopki_core_csr_fuzz ANOPKI_FUZZ_CSR)
    add_anopki_parser_fuzzer(anopki_core_ocsp_fuzz ANOPKI_FUZZ_OCSP)
    add_anopki_parser_fuzzer(anopki_core_crl_fuzz ANOPKI_FUZZ_CRL)
endif()

include(CTest)

if(BUILD_TESTING)
    add_executable(anopki_version_test tests/version_test.cpp)
    target_link_libraries(anopki_version_test PRIVATE anopki::core)
    add_test(NAME anopki.version COMMAND anopki_version_test)

    add_executable(anopki_enterprise_edition_metadata_test enterprise/tests/edition_metadata_test.cpp)
    target_link_libraries(anopki_enterprise_edition_metadata_test PRIVATE anopki::core)
    add_test(NAME enterprise.edition_metadata COMMAND anopki_enterprise_edition_metadata_test)
    set_tests_properties(enterprise.edition_metadata PROPERTIES LABELS "enterprise_metadata")

    add_executable(anopki_crypto_backend_interface_test tests/crypto_backend_interface_test.cpp)
    target_link_libraries(anopki_crypto_backend_interface_test PRIVATE anopki::core)
    add_test(NAME anopki.crypto_backend_interface COMMAND anopki_crypto_backend_interface_test)

    add_executable(anopki_backend_profile_test tests/backend_validation_checks_test.cpp)
    target_link_libraries(anopki_backend_profile_test PRIVATE anopki::core ${ANOPKI_SELECTED_ADAPTER_TARGET})
    target_compile_definitions(anopki_backend_profile_test PRIVATE
        ANOPKI_EXPECTED_TEST_PROFILE="${ANOPKI_PRODUCT_PROFILE}")
    add_test(NAME anopki.backend_profile COMMAND anopki_backend_profile_test)
    add_test(NAME anopki.backend_validation_checks COMMAND anopki_backend_profile_test --fixtures)

    if(ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-openssl")
        add_executable(anopki_core_cli_contract_test tests/core_cli_contract_test.cpp)
        target_link_libraries(anopki_core_cli_contract_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_dependencies(anopki_core_cli_contract_test anopki-core)
        add_test(NAME anopki.core_cli_contract COMMAND anopki_core_cli_contract_test $<TARGET_FILE:anopki-core> ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/ocsp enterprise-openssl enterprise)

        add_executable(anopki_core_issue_profile_test tests/core_issue_profile_test.cpp)
        target_link_libraries(anopki_core_issue_profile_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_dependencies(anopki_core_issue_profile_test anopki-core)
        add_test(NAME anopki.core_issue_profile COMMAND anopki_core_issue_profile_test $<TARGET_FILE:anopki-core> ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anopki_core_crl_test tests/core_crl_test.cpp)
        target_link_libraries(anopki_core_crl_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.core_crl COMMAND anopki_core_crl_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anopki_core_ocsp_test tests/core_ocsp_test.cpp)
        target_link_libraries(anopki_core_ocsp_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.core_ocsp COMMAND anopki_core_ocsp_test ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/ocsp)

        add_executable(anopki_core_openssl_golden_test tests/core_openssl_golden_test.cpp)
        target_link_libraries(anopki_core_openssl_golden_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.core_openssl_golden COMMAND anopki_core_openssl_golden_test ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/backend-parity)

        add_executable(anopki_crl_file_key_provider_test tests/crl_file_key_provider_test.cpp)
        target_link_libraries(anopki_crl_file_key_provider_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.crl_file_key_provider COMMAND anopki_crl_file_key_provider_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anopki_ocsp_file_key_provider_test tests/ocsp_file_key_provider_test.cpp)
        target_link_libraries(anopki_ocsp_file_key_provider_test PRIVATE anopki::core anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.ocsp_file_key_provider COMMAND anopki_ocsp_file_key_provider_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anopki_file_key_provider_test tests/file_key_provider_test.cpp)
        target_include_directories(anopki_file_key_provider_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/backends/openssl)
        target_link_libraries(anopki_file_key_provider_test PRIVATE anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.file_key_provider COMMAND anopki_file_key_provider_test)

        add_executable(anopki_software_token_key_provider_test tests/software_token_key_provider_test.cpp)
        target_include_directories(anopki_software_token_key_provider_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/backends/openssl)
        target_link_libraries(anopki_software_token_key_provider_test PRIVATE anopki::openssl_adapter OpenSSL::Crypto)
        add_test(NAME anopki.software_token_key_provider COMMAND anopki_software_token_key_provider_test)

        find_package(Python3 REQUIRED COMPONENTS Interpreter)
        add_test(NAME anopki.key_provider_boundary COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/validate-key-provider-boundary.py --root ${CMAKE_CURRENT_SOURCE_DIR})
        add_test(NAME anopki.key_provider_boundary_validator_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test_validate_key_provider_boundary.py)
    else()
        find_package(Python3 REQUIRED COMPONENTS Interpreter)
        add_executable(anocrypto_sdk_integration_test enterprise/tests/anocrypto_sdk_integration_test.cpp)
        target_include_directories(anocrypto_sdk_integration_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
        target_link_libraries(anocrypto_sdk_integration_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter)
        add_test(NAME anocrypto.sdk_integration COMMAND anocrypto_sdk_integration_test)
        set_tests_properties(anocrypto.sdk_integration PROPERTIES LABELS "anocrypto_sdk_integration")
        add_test(NAME anocrypto.runtime_evidence_checks
            COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test_anocrypto_runtime_evidence.py
                $<TARGET_FILE:anocrypto_sdk_integration_test>)

        add_executable(anocrypto_no_fallback_test enterprise/tests/anocrypto_no_fallback_test.cpp)
        target_link_libraries(anocrypto_no_fallback_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter AnoCryptoC::AnoCryptoC)
        add_test(NAME anocrypto.no_fallback COMMAND anocrypto_no_fallback_test ${CMAKE_CURRENT_BINARY_DIR})
        set_tests_properties(anocrypto.no_fallback PROPERTIES LABELS "anocrypto_no_fallback")

        find_package(OpenSSL REQUIRED COMPONENTS Crypto)
        add_executable(anocrypto_parity_test tests/core_openssl_golden_test.cpp)
        target_link_libraries(anocrypto_parity_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anopki.crypto_backend_parity.anocrypto COMMAND anocrypto_parity_test ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/backend-parity)
        set_tests_properties(anopki.crypto_backend_parity.anocrypto PROPERTIES LABELS "anocrypto_parity")

        add_executable(anocrypto_crl_test tests/core_crl_test.cpp)
        target_link_libraries(anocrypto_crl_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anocrypto.crl COMMAND anocrypto_crl_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anocrypto_ocsp_test tests/core_ocsp_test.cpp)
        target_link_libraries(anocrypto_ocsp_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anocrypto.ocsp COMMAND anocrypto_ocsp_test ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/ocsp)

        add_executable(anocrypto_crl_file_key_provider_test tests/crl_file_key_provider_test.cpp)
        target_link_libraries(anocrypto_crl_file_key_provider_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anocrypto.crl_file_key_provider COMMAND anocrypto_crl_file_key_provider_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anocrypto_ocsp_file_key_provider_test tests/ocsp_file_key_provider_test.cpp)
        target_link_libraries(anocrypto_ocsp_file_key_provider_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anocrypto.ocsp_file_key_provider COMMAND anocrypto_ocsp_file_key_provider_test ${CMAKE_CURRENT_BINARY_DIR})

        add_executable(anocrypto_pki_algorithms_test enterprise/tests/anocrypto_pki_algorithms_test.cpp)
        target_link_libraries(anocrypto_pki_algorithms_test PRIVATE anopki::core anopki_enterprise_anocrypto_adapter OpenSSL::Crypto)
        add_test(NAME anocrypto.pki_algorithms COMMAND anocrypto_pki_algorithms_test ${CMAKE_CURRENT_BINARY_DIR})
        set_tests_properties(anocrypto.pki_algorithms PROPERTIES LABELS "anocrypto_parity;anocrypto_algorithms")
        set_tests_properties(anocrypto.no_fallback PROPERTIES DEPENDS anocrypto.pki_algorithms)

        set(ANOPKI_DEPENDENCY_TOOL "${CMAKE_LINKER}")
        set(ANOPKI_BOUNDARY_FIXTURE_ARGS)
        set(ANOPKI_MISSING_SDK_ARGS --executable $<TARGET_FILE:anopki_backend_profile_test>)
        if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
            if(NOT CMAKE_READELF OR NOT EXISTS "${CMAKE_READELF}")
                message(FATAL_ERROR "AnoCrypto dependency purity requires a supported ELF reader (readelf)")
            endif()
            set(ANOPKI_DEPENDENCY_TOOL "${CMAKE_READELF}")
            set(ANOPKI_BOUNDARY_FIXTURE_ARGS
                --elf-reader "${CMAKE_READELF}"
                --clean-artifact $<TARGET_FILE:anopki-core>
                --openssl-artifact $<TARGET_FILE:anocrypto_parity_test>
            )
            add_executable(anocrypto_missing_sdk_probe enterprise/tests/anocrypto_missing_sdk_probe.cpp)
            target_link_libraries(anocrypto_missing_sdk_probe PRIVATE AnoCryptoC::AnoCryptoC ${CMAKE_DL_LIBS})
            set_target_properties(anocrypto_missing_sdk_probe PROPERTIES SKIP_BUILD_RPATH TRUE)
            set(ANOPKI_MISSING_SDK_ARGS
                --executable $<TARGET_FILE:anocrypto_missing_sdk_probe>
                --sdk-library $<TARGET_FILE:AnoCryptoC::AnoCryptoC>
                --sdk-soname $<TARGET_SONAME_FILE_NAME:AnoCryptoC::AnoCryptoC>
            )
        endif()

        add_test(
            NAME anocrypto.dependency_purity
            COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/scripts/validate-anocrypto-boundary.py
                --root ${CMAKE_CURRENT_SOURCE_DIR}
                --dependency-tool "${ANOPKI_DEPENDENCY_TOOL}"
                --artifact runtime=$<TARGET_FILE:anopki-core>
                --artifact adapter=$<TARGET_FILE:anopki_enterprise_anocrypto_adapter>
                --artifact sdk=$<TARGET_FILE:AnoCryptoC::AnoCryptoC>
                --artifact test-sdk-integration=$<TARGET_FILE:anocrypto_sdk_integration_test>
                --artifact test-no-fallback=$<TARGET_FILE:anocrypto_no_fallback_test>
        )
        set_tests_properties(anocrypto.dependency_purity PROPERTIES LABELS "anocrypto_dependency_purity")
        add_test(
            NAME anocrypto.boundary_validator_tests
            COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test_validate_anocrypto_boundary.py
                ${ANOPKI_BOUNDARY_FIXTURE_ARGS}
        )
        add_test(
            NAME anocrypto.missing_dependency_no_fallback
            COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test-anocrypto-missing-dependency.py
                ${ANOPKI_MISSING_SDK_ARGS}
        )
        set_tests_properties(anocrypto.missing_dependency_no_fallback PROPERTIES LABELS "anocrypto_no_fallback")

        foreach(target
            anopki_backend_profile_test
            anocrypto_sdk_integration_test
            anocrypto_no_fallback_test
            anocrypto_parity_test
            anocrypto_crl_test
            anocrypto_ocsp_test
            anocrypto_crl_file_key_provider_test
            anocrypto_ocsp_file_key_provider_test
            anocrypto_pki_algorithms_test
        )
            anopki_stage_anocrypto_runtime(${target})
        endforeach()

        if(WIN32)
            get_filename_component(ANOPKI_TEST_OPENSSL_ROOT "${OPENSSL_INCLUDE_DIR}" DIRECTORY)
            set(ANOPKI_TEST_OPENSSL_RUNTIME_DIR "${ANOPKI_TEST_OPENSSL_ROOT}/bin")
            string(REPLACE ";" "\\;" ANOPKI_TEST_INHERITED_PATH "$ENV{PATH}")
            set_tests_properties(
                anopki.crypto_backend_parity.anocrypto
                anocrypto.crl
                anocrypto.ocsp
                anocrypto.crl_file_key_provider
                anocrypto.ocsp_file_key_provider
                anocrypto.pki_algorithms
                PROPERTIES ENVIRONMENT
                    "PATH=${ANOPKI_TEST_OPENSSL_RUNTIME_DIR}\\;${ANOPKI_TEST_INHERITED_PATH}"
            )
        endif()
    endif()
endif()
