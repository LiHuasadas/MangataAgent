"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useAppendVideoFragment = exports.appendVideoFragment = exports.isIosSafari = exports.isSafari = void 0;
const react_1 = require("react");
const toSeconds = (time, fps) => {
    return Math.round((time / fps) * 100) / 100;
};
const isSafari = () => {
    if (typeof window === 'undefined') {
        return false;
    }
    const isAppleWebKit = /AppleWebKit/.test(window.navigator.userAgent);
    if (!isAppleWebKit) {
        return false;
    }
    const isNotChrome = !window.navigator.userAgent.includes('Chrome/');
    return isNotChrome;
};
exports.isSafari = isSafari;
const isIosSafari = () => {
    if (typeof window === 'undefined') {
        return false;
    }
    const { userAgent, platform, maxTouchPoints } = window.navigator;
    const isIpadIPodIPhone = /iP(ad|od|hone)/i.test(userAgent);
    // Since iPadOS 13, Safari on iPad defaults to "Request Desktop Website"
    // and sends a macOS user agent ("Macintosh; Intel Mac OS X 10_15_7"),
    // so the string above never matches. A Mac platform with a touch
    // screen is the only remaining signal — real Macs report 0 touch
    // points. Without this, iPads get the blob + media fragment
    // combination that Mobile Safari refuses to play (#1655).
    const isIpadOsDesktopMode = platform === 'MacIntel' && maxTouchPoints > 1;
    return (isIpadIPodIPhone || isIpadOsDesktopMode) && (0, exports.isSafari)();
};
exports.isIosSafari = isIosSafari;
// https://github.com/remotion-dev/remotion/issues/1655
const isIOSSafariAndBlob = (actualSrc) => {
    return (0, exports.isIosSafari)() && actualSrc.startsWith('blob:');
};
const getVideoFragmentStart = ({ actualFrom, fps, }) => {
    return toSeconds(Math.max(0, -actualFrom), fps);
};
const getVideoFragmentEnd = ({ duration, fps, }) => {
    return toSeconds(duration, fps);
};
const appendVideoFragment = ({ actualSrc, actualFrom, duration, fps, }) => {
    var _a;
    if (isIOSSafariAndBlob(actualSrc)) {
        return actualSrc;
    }
    if (actualSrc.startsWith('data:')) {
        return actualSrc;
    }
    const existingHash = Boolean(new URL(actualSrc, (_a = (typeof window === 'undefined' ? null : window.location.href)) !== null && _a !== void 0 ? _a : 'http://localhost:3000').hash);
    if (existingHash) {
        return actualSrc;
    }
    if (!Number.isFinite(actualFrom)) {
        return actualSrc;
    }
    const withStartHash = `${actualSrc}#t=${getVideoFragmentStart({ actualFrom, fps })}`;
    if (!Number.isFinite(duration)) {
        return withStartHash;
    }
    return `${withStartHash},${getVideoFragmentEnd({ duration, fps })}`;
};
exports.appendVideoFragment = appendVideoFragment;
const isSubsetOfDuration = ({ prevStartFrom, newStartFrom, prevDuration, newDuration, fps, }) => {
    const previousFrom = getVideoFragmentStart({ actualFrom: prevStartFrom, fps });
    const newFrom = getVideoFragmentStart({ actualFrom: newStartFrom, fps });
    const previousEnd = getVideoFragmentEnd({ duration: prevDuration, fps });
    const newEnd = getVideoFragmentEnd({ duration: newDuration, fps });
    if (newFrom < previousFrom) {
        return false;
    }
    if (newEnd > previousEnd) {
        return false;
    }
    return true;
};
const useAppendVideoFragment = ({ actualSrc: initialActualSrc, actualFrom: initialActualFrom, duration: initialDuration, fps, }) => {
    const actualFromRef = (0, react_1.useRef)(initialActualFrom);
    const actualDuration = (0, react_1.useRef)(initialDuration);
    const actualSrc = (0, react_1.useRef)(initialActualSrc);
    if (!isSubsetOfDuration({
        prevStartFrom: actualFromRef.current,
        newStartFrom: initialActualFrom,
        prevDuration: actualDuration.current,
        newDuration: initialDuration,
        fps,
    }) ||
        initialActualSrc !== actualSrc.current) {
        actualFromRef.current = initialActualFrom;
        actualDuration.current = initialDuration;
        actualSrc.current = initialActualSrc;
    }
    const appended = (0, exports.appendVideoFragment)({
        actualSrc: actualSrc.current,
        actualFrom: actualFromRef.current,
        duration: actualDuration.current,
        fps,
    });
    return appended;
};
exports.useAppendVideoFragment = useAppendVideoFragment;
