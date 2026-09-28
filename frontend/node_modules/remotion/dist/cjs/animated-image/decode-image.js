"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decodeImage = void 0;
const create_image_decoder_1 = require("./create-image-decoder");
const CACHE_SIZE = 5;
const getActualTime = ({ loopBehavior, durationFound, timeInSec, }) => {
    return loopBehavior === 'loop'
        ? durationFound
            ? timeInSec % durationFound
            : timeInSec
        : Math.min(timeInSec, durationFound || Infinity);
};
const decodeImage = async ({ resolvedSrc, signal, requestInit, currentTime, initialLoopBehavior, }) => {
    const { decoder, selectedTrack } = await (0, create_image_decoder_1.createImageDecoder)({
        resolvedSrc,
        signal,
        requestInit,
        contentType: null,
    });
    const cache = [];
    let durationFound = null;
    const getFrameByIndex = async (frameIndex) => {
        const foundInCache = cache.find((c) => c.frameIndex === frameIndex);
        if (foundInCache && foundInCache.frame) {
            return foundInCache;
        }
        const frame = await decoder.decode({
            frameIndex,
            completeFramesOnly: true,
        });
        if (foundInCache) {
            foundInCache.frame = frame.image;
        }
        else {
            cache.push({
                frame: frame.image,
                frameIndex,
                timeInSeconds: frame.image.timestamp / 1000000,
            });
        }
        return {
            frame: frame.image,
            frameIndex,
            timeInSeconds: frame.image.timestamp / 1000000,
        };
    };
    const clearCache = (closeToTimeInSec) => {
        const itemsInCache = cache.filter((c) => c.frame);
        const sortByClosestToCurrentTime = itemsInCache.sort((a, b) => {
            const aDiff = Math.abs(a.timeInSeconds - closeToTimeInSec);
            const bDiff = Math.abs(b.timeInSeconds - closeToTimeInSec);
            return aDiff - bDiff;
        });
        for (let i = 0; i < sortByClosestToCurrentTime.length; i++) {
            if (i < CACHE_SIZE) {
                continue;
            }
            const item = sortByClosestToCurrentTime[i];
            item.frame = null;
        }
    };
    const ensureFrameBeforeAndAfter = async ({ timeInSec, loopBehavior, }) => {
        const actualTimeInSec = getActualTime({
            durationFound,
            loopBehavior,
            timeInSec,
        });
        const framesBefore = cache.filter((c) => c.timeInSeconds <= actualTimeInSec);
        const biggestIndex = framesBefore
            .map((c) => c.frameIndex)
            .reduce((a, b) => Math.max(a, b), 0);
        let i = biggestIndex;
        while (true) {
            const f = await getFrameByIndex(i);
            i++;
            if (!f.frame) {
                throw new Error('No frame found');
            }
            if (!f.frame.duration) {
                // non-animated, or AVIF in firefox
                break;
            }
            if (i === selectedTrack.frameCount && durationFound === null) {
                const duration = (f.frame.timestamp + f.frame.duration) / 1000000;
                durationFound = duration;
            }
            if (f.timeInSeconds > actualTimeInSec || i === selectedTrack.frameCount) {
                break;
            }
        }
        // If close to end, also cache first frame for smooth wrap around
        if (selectedTrack.frameCount - biggestIndex < 3 &&
            loopBehavior === 'loop') {
            await getFrameByIndex(0);
        }
        clearCache(actualTimeInSec);
    };
    // Twice because might be over total duration
    await ensureFrameBeforeAndAfter({
        timeInSec: currentTime,
        loopBehavior: initialLoopBehavior,
    });
    await ensureFrameBeforeAndAfter({
        timeInSec: currentTime,
        loopBehavior: initialLoopBehavior,
    });
    const getFrame = async (timeInSec, loopBehavior) => {
        if (durationFound !== null &&
            timeInSec > durationFound &&
            loopBehavior === 'clear-after-finish') {
            return null;
        }
        const actualTimeInSec = getActualTime({
            loopBehavior,
            durationFound,
            timeInSec,
        });
        await ensureFrameBeforeAndAfter({ timeInSec: actualTimeInSec, loopBehavior });
        const itemsInCache = cache.filter((c) => c.frame);
        const closest = itemsInCache.reduce((a, b) => {
            const aDiff = Math.abs(a.timeInSeconds - actualTimeInSec);
            const bDiff = Math.abs(b.timeInSeconds - actualTimeInSec);
            return aDiff < bDiff ? a : b;
        });
        if (!closest.frame) {
            throw new Error('No frame found');
        }
        return closest;
    };
    return {
        close: () => {
            var _a;
            for (const item of cache) {
                (_a = item.frame) === null || _a === void 0 ? void 0 : _a.close();
                item.frame = null;
            }
            decoder.close();
        },
        getFrame,
        frameCount: selectedTrack.frameCount,
    };
};
exports.decodeImage = decodeImage;
