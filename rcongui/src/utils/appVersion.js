
// function that returns the app version
export default function appVersion() {
    // REACT_APP_VERSION doesn't work... maybe due to the vite build?
    //return process.env.REACT_APP_VERSION;
    return "{version-tag}";
}