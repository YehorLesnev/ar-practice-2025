from dataclasses import dataclass
import numpy as np
import cv2


@dataclass
class SparseResult:
    old_pixels: np.ndarray
    new_pixels: np.ndarray
    old_points: np.ndarray
    new_points: np.ndarray
    original_points: np.ndarray
    valid_positions: np.ndarray


class IOpticalFlow:
    '''Interface of OpticalFlow classes'''
    def set1stFrame(self, frame):
        '''Set the starting frame'''
        self.prev = frame

    def apply(self, frame):
        '''Apply and return result display image (expected to be new object)'''
        result = frame.copy()
        self.prev = frame
        return result, None

class DenseOpticalFlow(IOpticalFlow):
    '''Abstract class for DenseOpticalFlow expressions'''
    def __init__(self):
        self.prev = None
        return super().__init__()

    def set1stFrame(self, frame):
        self.prev = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.hsv = np.zeros_like(frame)
        self.hsv[..., 1] = 255

    def apply(self, frame):
        if self.prev is None:
            self.set1stFrame(frame)

        next = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        flow = cv2.calcOpticalFlowFarneback(self.prev, next, None,
                                            0.5, 3, 15, 3, 5, 1.2, 0)

        result = self.makeResult(next, flow)
        self.prev = next
        return result, flow

    def makeResult(self, grayFrame, flow):
        '''Replace this for each expression'''
        return grayFrame.copy()

class DenseOpticalFlowByHSV(DenseOpticalFlow):
    def makeResult(self, grayFrame, flow):
        mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1])
        self.hsv[...,0] = ang*180/np.pi/2
        self. hsv[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.cvtColor(self.hsv, cv2.COLOR_HSV2BGR)

class DenseOpticalFlowByLines(DenseOpticalFlow):
    def __init__(self):
        self.step = 64 # configure this if you need other steps...
        return super().__init__()

    def makeResult(self, grayFrame, flow):
        h, w = grayFrame.shape[:2]
        y, x = np.mgrid[self.step//2:h:self.step, self.step//2:w:self.step].reshape(2,-1)
        fx, fy = flow[y,x].T
        lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        vis = cv2.cvtColor(grayFrame, cv2.COLOR_GRAY2BGR)
        cv2.polylines(vis, lines, 0, (0, 255, 0))
        for (x1, y1), (x2, y2) in lines:
            cv2.circle(vis, (x1, y1), 1, (0, 255, 0), -1)
        return vis

class DenseOpticalFlowByWarp(DenseOpticalFlow):
    def makeResult(self, grayFrame, flow):
        h, w = flow.shape[:2]
        flow = -flow
        flow[:,:,0] += np.arange(w)
        flow[:,:,1] += np.arange(h)[:,np.newaxis]
        return cv2.remap(grayFrame, flow, None, cv2.INTER_LINEAR)

class LucasKanadeOpticalFlow(IOpticalFlow):
    def __init__(self, feature_params=None, lk_params=None):
        # params for ShiTomasi corner detection
        if feature_params is None:
            feature_params = dict( maxCorners = 100,
                                      qualityLevel = 0.3,
                                      minDistance = 7,
                                      blockSize = 7 )

        # Parameters for Lucas-Kanade optical flow
        if lk_params is None:
            lk_params = dict( winSize  = (15,15),
                               maxLevel = 2,
                               criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.feature_params = feature_params
        self.lk_params = lk_params

        self.p0 = None
        self.old_gray = None
        return super().__init__()

    def set1stFrame(self, frame):
        self.old_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.p0 = cv2.goodFeaturesToTrack(self.old_gray, mask = None, **self.feature_params)

    def apply(self, frame):
        if self.p0 is None:
            self.set1stFrame(frame)

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, frame_gray,
                                               self.p0, None, **self.lk_params)

        # Select good points
        good_new = p1[st==1]
        good_old = self.p0[st==1]

        centerpoint = np.array([frame_gray.shape[1] // 2, frame_gray.shape[0] // 2])
        old_points = good_old - centerpoint
        new_points = good_new - centerpoint

        # Update the previous frame and previous points
        self.old_gray = frame_gray.copy()
        self.p0 = good_new.reshape(-1, 1, 2)

        # Pixels are calculated from top left corner of the image,
        # points are calculated from the center of the image.
        sparse_result = SparseResult(
            old_pixels = good_old,
            new_pixels = good_new,
            old_points = old_points,
            new_points = new_points,
            original_points = self.p0,
            valid_positions = st,

        )
        return frame, sparse_result


def CreateOpticalFlow(type):
    '''Optical flow showcase factory, call by type as shown below'''
    def dense_by_hsv():
        return DenseOpticalFlowByHSV()
    def dense_by_lines():
        return DenseOpticalFlowByLines()
    def dense_by_warp():
        return DenseOpticalFlowByWarp()
    def lucas_kanade():
        return LucasKanadeOpticalFlow()
    return {
        'dense_hsv': dense_by_hsv,
        'dense_lines': dense_by_lines,
        'dense_warp': dense_by_warp,
        'lucas_kanade': lucas_kanade
    }.get(type, dense_by_lines)()
