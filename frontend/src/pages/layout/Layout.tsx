import { Outlet, Link } from "react-router-dom";
import styles from "./Layout.module.css";
import Octo from "../../assets/octo.png"
import { CopyRegular } from "@fluentui/react-icons";
import { DefaultButton, PrimaryButton, Dialog, Stack, TextField, ChoiceGroup, IChoiceGroupOption, Toggle } from "@fluentui/react";
import { SetStateAction, useContext, useEffect, useState } from "react";
import { HistoryButton, ShareButton, SettingsButton } from "../../components/common/Button";
import { AppStateContext } from "../../state/AppProvider";
import { CosmosDBStatus, FrontendSettings, writeFrontendSettings } from "../../api";

const Layout = () => {
    const [isSharePanelOpen, setIsSharePanelOpen] = useState<boolean>(false);
    const [isSettingsPanelOpen, setIsSettingsPanelOpen] = useState<boolean>(false);
    const [copyClicked, setCopyClicked] = useState<boolean>(false);
    const [copyText, setCopyText] = useState<string>("Copy URL");
    const [saveSettingsClicked, setSaveSettingsClicked] = useState<boolean>(false);
    const [saveSettingsText, setSaveSettingsText] = useState<string>("");
    const [authEnabled, setAuthEnabled] = useState<boolean>(false);
    const [feedbackEnabled, setFeedbackEnabled] = useState<boolean>(false);
    const [headerTitle, setHeaderTitle] = useState<string>("");
    const [pageTabTitle, setPageTabTitle] = useState<string>("");
    const [aiDeployments, setAIDeployments] = useState<string>("");
    const [aiModel, setAIModel] = useState<string>("");
    const [deploymentLabel, setDeploymentLabel] = useState<string>("No Deployment Model defined yet.");
    const [aiModelChoices, setAIModelChoices] = useState<IChoiceGroupOption[]>([]);
    const appStateContext = useContext(AppStateContext);
    const ui = appStateContext?.state.frontendSettings?.ui;

    const handleShareClick = () => {
        setIsSharePanelOpen(true);
    };

    const handleSharePanelDismiss = () => {
        setIsSharePanelOpen(false);
        setCopyClicked(false);
        setCopyText("Copy URL");
    };

    const handleSettingsClick = () => {
        setIsSettingsPanelOpen(true);

        // Set controls to values in appsettings.json
        setAuthEnabled(appStateContext?.state.frontendSettings?.auth_enabled == true ? true : false);
        setFeedbackEnabled(appStateContext?.state.frontendSettings?.feedback_enabled == true ? true : false);
        setHeaderTitle(appStateContext?.state.frontendSettings?.header_title!);
        setPageTabTitle(appStateContext?.state.frontendSettings?.page_tab_title!);
        setAIDeployments(appStateContext?.state.frontendSettings?.azure_openai_deployments!);
        setAIModel(appStateContext?.state.frontendSettings?.azure_openai_model!);
    };

    const splitChoices = (choices: string) => {
        const modelList = choices.split(",");
        let choiceGroup: IChoiceGroupOption[] = []; 

        for (let i=0; i < modelList.length; i++) {
            choiceGroup.push({key: modelList[i], text: modelList[i]});
        }

        return choiceGroup;
    };

    const handleSettingsPanelDismiss = () => {
        setIsSettingsPanelOpen(false);
        setSaveSettingsText("");
    };

    const handleCopyClick = () => {
        navigator.clipboard.writeText(window.location.href);
        setCopyClicked(true);
    };

    const handleHistoryClick = () => {
        appStateContext?.dispatch({ type: 'TOGGLE_CHAT_HISTORY' })
    };

    const saveFrontendSettings = async () => {
        const settings: FrontendSettings = {
            auth_enabled: authEnabled,
            feedback_enabled: feedbackEnabled,
            header_title: headerTitle,
            page_tab_title: pageTabTitle,
            azure_openai_deployments: aiDeployments,
            azure_openai_model: aiModel
        }

        console.log("Frontend Settings being saved... " + JSON.stringify(settings));

        // Save the updated settings to appsettings.json file
        writeFrontendSettings(settings).then((response) => {
            appStateContext?.dispatch({ type: 'SET_FRONTEND_SETTINGS', payload: settings });
            console.log("Saved Frontend Settings successfully.");
        })
        .catch((err) => {
            console.error("There was an issue saving the updated frontend settings.  " + err);
        })
    }

    const handleSaveSettingsClick = () => {
        saveFrontendSettings();
        setSaveSettingsClicked(true);
        setSaveSettingsText("Settings saved.");
    };

    const handleAuthEnabledChange = (event: any, checked?: boolean | undefined) => {
        setAuthEnabled(checked!);
    }

    const handleFeedbackEnabledChange = (event: any, checked?: boolean | undefined) => {
        setFeedbackEnabled(checked!);
    }

    const handleHeaderTitleChange = (event: any, newValue?: string | undefined) => {
        setHeaderTitle(newValue!);
    }

    const handlePageTabTitleChange = (event: any, newValue?: string | undefined) => {
        setPageTabTitle(newValue!);
    }

    const handleAIModelChange = (event: any, option?: IChoiceGroupOption | undefined) => {
        setAIModel(option?.text!);
    }

    useEffect(() => {
        if (copyClicked) {
            setCopyText("Copied URL");
        }
    }, [copyClicked]);

    useEffect(() => {
        if (saveSettingsClicked) {
            setSaveSettingsText("Settings saved.");
        }
    }, [saveSettingsClicked]);

    useEffect(() => { }, [appStateContext?.state.isCosmosDBAvailable.status]);

    useEffect(() => {
        let title = appStateContext?.state.frontendSettings?.page_tab_title ?? "Configure Page Tab Title";
        console.log("Page Tab Title setting: " + appStateContext?.state.frontendSettings?.page_tab_title);
        document.title = title.toString();
    }, [appStateContext?.state.frontendSettings?.page_tab_title]);

    useEffect(() => {
        let choices = appStateContext?.state.frontendSettings?.azure_openai_deployments ?? "";
        setAIModelChoices(splitChoices(choices));
    }, [appStateContext?.state.frontendSettings?.azure_openai_deployments]);

    useEffect(() => {
        let deployment = appStateContext?.state.frontendSettings?.azure_openai_model ?? "Not defined";
        setDeploymentLabel("Azure OpenAI Deployment Model in use: [" + deployment + "]");
        console.log(deploymentLabel);
    }, [appStateContext?.state.frontendSettings?.azure_openai_model]);

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"} title={deploymentLabel}>
                <Stack horizontal verticalAlign="center" horizontalAlign="space-between">
                    <Stack horizontal verticalAlign="center">
                        <img
                            src={Octo}
                            className={styles.headerIcon}
                            aria-hidden="true"
                        />
                        <Link to="/" className={styles.headerTitleContainer}>
                            <h1 className={styles.headerTitle}>{appStateContext?.state.frontendSettings?.header_title}</h1>
                        </Link>
                    </Stack>                    
                    <Stack horizontal tokens={{ childrenGap: 4 }}>
                        {(appStateContext?.state.isCosmosDBAvailable?.status !== CosmosDBStatus.NotConfigured) &&
                            <HistoryButton onClick={handleHistoryClick} text={appStateContext?.state?.isChatHistoryOpen ? "Hide chat history" : "Show chat history"} />
                        }
                        <ShareButton onClick={handleShareClick} />
                        <SettingsButton onClick={handleSettingsClick} />
                    </Stack>
                </Stack>
            </header>
            <Outlet />
            <Dialog
                onDismiss={handleSharePanelDismiss}
                hidden={!isSharePanelOpen}
                styles={{
                    main: [{
                        selectors: {
                            ['@media (min-width: 480px)']: {
                                maxWidth: '600px',
                                background: "#FFFFFF",
                                boxShadow: "0px 14px 28.8px rgba(0, 0, 0, 0.24), 0px 0px 8px rgba(0, 0, 0, 0.2)",
                                borderRadius: "8px",
                                maxHeight: '200px',
                                minHeight: '100px',
                            }
                        }
                    }]
                }}
                dialogContentProps={{
                    title: "Share the web app",
                    showCloseButton: true
                }}
            >
                <Stack horizontal verticalAlign="center" style={{ gap: "8px" }}>
                    <TextField className={styles.urlTextBox} defaultValue={window.location.href} readOnly />
                    <div
                        className={styles.copyButtonContainer}
                        role="button"
                        tabIndex={0}
                        aria-label="Copy"
                        onClick={handleCopyClick}
                        onKeyDown={e => e.key === "Enter" || e.key === " " ? handleCopyClick() : null}
                    >
                        <CopyRegular className={styles.copyButton} />
                        <span className={styles.copyButtonText}>{copyText}</span>
                    </div>
                </Stack>
            </Dialog>
            <Dialog
                onDismiss={handleSettingsPanelDismiss}
                hidden={!isSettingsPanelOpen}
                styles={{
                    main: [{
                        selectors: {
                            ['@media (min-width: 400px)']: {
                                background: "#FFFFFF",
                                boxShadow: "0px 14px 28.8px rgba(0, 0, 0, 0.24), 0px 0px 8px rgba(0, 0, 0, 0.2)",
                                borderRadius: "8px",
                                maxHeight: '550px',
                                minHeight: '200px',
                                maxWidth: '500px',
                                minWidth: '300px',
                                width: '400px',
                                height: '275px',
                            }
                        }
                    }]
                }}
                dialogContentProps={{
                    title: "Settings",
                    showCloseButton: true
                }}
            >
                <Stack verticalAlign="center" style={{ gap: "6px" }}>
            {/*   <Toggle 
                        id="AuthEnabledToggle"
                        label={"Auth Enabled?"} 
                        onChange={handleAuthEnabledChange}
                        checked={authEnabled}
                        disabled={true}> 
                    </Toggle>
                    <Toggle 
                        id="FeedbackEnabledToggle"
                        label={"Feedback Enabled?"} 
                        onChange={handleFeedbackEnabledChange}
                        checked={feedbackEnabled}
                        disabled={true}>
                    </Toggle>
                    <TextField id="HeaderTitleTextField" label="Header Title" value={headerTitle} onChange={handleHeaderTitleChange} />
                    <TextField id="PageTabTitleTextField" label="Page Tab Title" value={pageTabTitle} onChange={handlePageTabTitleChange} />
            */}
                    <ChoiceGroup 
                        id="AIModelChoiceGroup"
                        label="Azure OpenAI Deployment Name"
                        styles={{flexContainer: [{flexDirection: "row"}]}}
                        selectedKey={aiModel}
                        onChange={handleAIModelChange}
                        options={aiModelChoices}>
                    </ChoiceGroup>
                </Stack>
                <br/>
                <Stack horizontal verticalAlign="center" horizontalAlign="end" style={{ gap: "6px" }}>
                    <DefaultButton onClick={handleSaveSettingsClick}
                                   onKeyDown={e => e.key === "Enter" || e.key === " " ? handleSaveSettingsClick() : null}>
                        Save
                    </DefaultButton>
                    <PrimaryButton onClick={handleSettingsPanelDismiss}
                                   onKeyDown={e => e.key === "Enter" || e.key === " " ? handleSettingsPanelDismiss() : null}>
                        Close
                    </PrimaryButton>
                </Stack>
                <br></br>
                <Stack horizontal verticalAlign="center" horizontalAlign="center" style={{ gap: "8px", color: "green", fontStyle: "italic", fontWeight: "bold" }}>
                    <span>{saveSettingsText}</span>
                </Stack>
            </Dialog>            
        </div>
    );
};

export default Layout;
