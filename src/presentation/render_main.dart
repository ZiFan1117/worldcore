// ★ AI-OS A2UI 渲染器（Flutter 半）—— ★ 只画，不管世界。
//
// ★ 作者令（逐字，2026-10-18）：
//   ·「我们只用 A2UI，不用 GTK」      ⇒ ★ 渲染【只用 A2UI】（包 genui）
//   ·「Python 多个桥不行」            ⇒ ★ 桥【只有一个】：本机 TCP 127.0.0.1:7450
//   ·「保持人家原有的不动，只是给他一个协议」⇒ ★ genui 原封不动，我们只递单子
//
// ★ 它是什么：A2UI 渲染器（**不报个体**——它是 presentation 的实现，不是世界成员）。
// ★ 它不是什么：不连 zenoh、不落盘、不裁决。
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:genui/genui.dart' as genui;
import 'package:a2ui_core/a2ui_core.dart' as core;

const String kHost = String.fromEnvironment('HOST', defaultValue: '127.0.0.1');
const int kPort = int.fromEnvironment('PORT', defaultValue: 7450);

void main() => runApp(const AiosRenderApp());

class AiosRenderApp extends StatelessWidget {
  const AiosRenderApp({super.key});
  @override
  Widget build(BuildContext c) => MaterialApp(
        title: 'AI-OS',
        debugShowCheckedModeBanner: false,
        // ★ 2026-10-19：换成【亮色主题】（原来 dark ⇒ 屏上黑漆漆一片）
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF2F6FEB), brightness: Brightness.light),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xFFF4F7FC),
        ),
        home: const RenderScreen(),
      );
}

class RenderScreen extends StatefulWidget {
  const RenderScreen({super.key});
  @override
  State<RenderScreen> createState() => _RenderScreenState();
}

class _RenderScreenState extends State<RenderScreen> {
  Socket? _sock;
  final List<_Layer> _layers = [];
  // ★★★ 缓存：每个 surface 一个 controller（★ 帧没变就【复用】）
  //    ★ 否则 build() 里重建 ⇒ TextField 的输入被冲掉（作者现取：「输入东西没办法显示」）
  final Map<String, genui.SurfaceController> _ctlCache = {};
  final Map<String, String> _frameHash = {};
  String _name = '';
  String _status = '连成像器…';
  String _buf = '';
  int _frames = 0;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  Future<void> _connect() async {
    while (mounted) {
      try {
        final s = await Socket.connect(kHost, kPort, timeout: const Duration(seconds: 3));
        _sock = s;
        setState(() => _status = '已连成像器');
        s.cast<List<int>>().transform(utf8.decoder).listen((chunk) {
          _buf += chunk;
          while (_buf.contains('\n')) {
            final i = _buf.indexOf('\n');
            final line = _buf.substring(0, i).trim();
            _buf = _buf.substring(i + 1);
            if (line.isNotEmpty) _onLine(line);
          }
        }, onDone: () {
          setState(() => _status = '成像器断开，重连…');
          _sock = null;
        }, onError: (_) {
          setState(() => _status = '成像器出错，重连…');
          _sock = null;
        });
        return;
      } catch (_) {
        await Future<void>.delayed(const Duration(seconds: 2));
      }
    }
  }

  void _onLine(String line) {
    Map<String, dynamic> msg;
    try {
      msg = jsonDecode(line) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    if (msg['t'] == 'layout') {
      _onLayout(msg);
      return;
    }
    if (msg['t'] != 'frame') return;
    final sid = msg['surface'] as String?;
    final frame = msg['frame'] as Map<String, dynamic>?;
    if (sid == null || frame == null) return;

    if (!mounted) return;
    setState(() {
      _layers
        ..clear()
        ..add(_Layer(surface: sid, z: 0, rect: null, active: true, frame: frame));
      _name = (frame['name'] as String?) ?? '';
      _frames++;
      _status = 'surface=$sid  帧=$_frames';
    });
  }

  /// ★ 收到【合成清单】：按 z 叠、按 rect 摆。★ 渲染器【不布局】，只按清单摆。
  void _onLayout(Map<String, dynamic> msg) {
    final raw = (msg['layers'] as List?) ?? const [];
    final layers = <_Layer>[];
    for (final l in raw) {
      if (l is! Map) continue;
      final sid = l['surface'] as String?;
      final frame = l['frame'];
      if (sid == null || frame is! Map) continue;
      final rect = l['rect'];
      layers.add(_Layer(
        surface: sid,
        z: (l['z'] as num?)?.toInt() ?? 0,
        rect: (rect is List && rect.length == 4)
            ? Rect.fromLTWH((rect[0] as num).toDouble(), (rect[1] as num).toDouble(),
                (rect[2] as num).toDouble(), (rect[3] as num).toDouble())
            : null,
        active: l['active'] == true,
        frame: Map<String, dynamic>.from(frame),
      ));
    }
    if (!mounted) return;
    setState(() {
      _layers
        ..clear()
        ..addAll(layers);
      _frames++;
      _status = '层=${layers.length}  帧=$_frames';
      if (layers.isNotEmpty) _name = layers.first.surface;
    });
  }

  /// ★ 把【一帧 A2UI】喂进一个新的 controller（★ genui 原封不动，我们只递单子）
  genui.SurfaceController _feed(Map<String, dynamic> frame) {
    final ctl = genui.SurfaceController(
      catalogs: [genui.BasicCatalogItems.asNoAssetCatalog()],
    );
    for (final m in (frame['messages'] as List? ?? const [])) {
      if (m is! Map) continue;
      final mm = Map<String, dynamic>.from(m);
      mm['version'] = 'v0.9';
      final cs = mm['createSurface'];
      if (cs is Map) {
        final c2 = Map<String, dynamic>.from(cs);
        c2['catalogId'] =
            'https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json';
        mm['createSurface'] = c2;
      }
      try {
        ctl.handleMessage(core.A2uiMessage.fromJson(mm));
      } catch (e) {
        debugPrint('FEED FAIL: $e');
      }
    }
    // ★★★ 人的动作从这里出来（genui 逐字：`_surfaceController.onSubmit.listen(...)`）
    ctl.onSubmit.listen((msg) {
      _onUserAction(msg);
    });
    return ctl;
  }

  /// ★★ 从 ChatMessage 里挖出 {name, context, sourceComponentId}（★ 藏在 base64 data URL 里）
  Map<String, dynamic> _extractAction(Map<String, dynamic> payload) {
    try {
      final parts = payload['parts'];
      if (parts is! List || parts.isEmpty) return {};
      final c = (parts[0] as Map)['content'] as Map;
      final bytes = c['bytes'] as String? ?? '';
      final i = bytes.indexOf('base64,');
      if (i < 0) return {};
      final raw = utf8.decode(base64Decode(bytes.substring(i + 7)));
      final outer = jsonDecode(raw) as Map<String, dynamic>;
      var inner = outer['interaction'];
      if (inner is String) inner = jsonDecode(inner);
      if (inner is! Map) return {};
      final a = inner['action'];
      if (a is Map) return Map<String, dynamic>.from(a);
      if (inner['error'] is Map) {
        debugPrint('INTERACTION ERROR: ' + inner['error'].toString());
      }
      return {};
    } catch (e) {
      debugPrint('EXTRACT FAIL: ' + e.toString());
      return {};
    }
  }

  /// ★ genui 把【人点了什么】给成 ChatMessage ⇒ 我们原样回推给呈现（★ 一个桥）
  void _onUserAction(Object msg) {
    final sock = _sock;
    if (sock == null) return;
    Map<String, dynamic> payload = <String, dynamic>{};
    try {
      final dyn = msg as dynamic;
      final j = dyn.toJson();
      if (j is Map) payload = Map<String, dynamic>.from(j);
    } catch (_) {
      payload = {'text': msg.toString()};
    }
    // ★★★ genui 把【人的动作】封在 ChatMessage.parts[0].content.bytes 的
    //     data URL 里：data:application/vnd.genui.interaction+json;base64,<b64>
    //    b64 解开是 {"interaction":"{\"version\":\"v0.9\",\"action\":{...}}"}
    debugPrint('ACT-DIAG ' + _extractAction(payload).toString());
    final sid = _layers.isEmpty ? null : _layers.first.surface;
    final act = _extractAction(payload);
    final body = <String, dynamic>{
      't': 'act',
      'surface': sid,
      'action': act.isEmpty ? {'raw': payload['parts']} : act,
      'component': act['sourceComponentId'] ?? '',
    };
    // ★ 值在 action.context 里（★ genui 解析），不用自己读 DataModel
    sock.write(jsonEncode(body) + '\n');
    debugPrint('ACT → 呈现: ' + body.toString());
  }

  Future<void> _sendAct(String component, Map<String, dynamic> action) async {
    final sock = _sock;
    if (sock == null) return;
    // ★ 把人【输入的值】一起带回去（★ A2UI 的 dataModel）——
    //   不然 space 收不到用户名/密码（★ 登录就白点了）
    final dm = <String, dynamic>{};
    for (final l in _layers) {
      final ctl = _feed(l.frame);
      final sids = ctl.activeSurfaceIds.toList();
      if (sids.isEmpty) continue;
      try {
        final model = ctl.contextFor(sids.first).dataModel;
      } catch (e) {
        debugPrint('READ DATA MODEL FAIL: $e');
      }
    }
    sock.write(jsonEncode({
      't': 'act',
      'surface': _layers.isEmpty ? null : _layers.first.surface,
      'component': component,
      'action': action,
      'dataModel': dm,
    }) + '\n');
  }


  @override
  Widget build(BuildContext context) {
    // ★ 按【合成清单】叠：z 已由呈现排好；rect 为空的层铺满
    final stack = <Widget>[];
    for (final l in _layers) {
      // ★★ 同一个 surface ∧ 同一帧 ⇒ 【复用】controller（★ 保住输入框里的字）
      final h = l.frame.toString();
      if (_ctlCache[l.surface] == null || _frameHash[l.surface] != h) {
        _ctlCache[l.surface] = _feed(l.frame);
        _frameHash[l.surface] = h;
      }
      final ctl = _ctlCache[l.surface]!;
      final sids = ctl.activeSurfaceIds.toList();
      if (sids.isEmpty) continue;
      final child = genui.Surface(
        surfaceContext: ctl.contextFor(sids.first),
        defaultBuilder: (_) => const SizedBox.shrink(),
      );
      if (l.rect == null) {
        stack.add(Positioned.fill(child: child));
      } else {
        stack.add(Positioned(
          left: l.rect!.left,
          top: l.rect!.top,
          width: l.rect!.width,
          height: l.rect!.height,
          child: child,
        ));
      }
    }
    return Scaffold(
      body: DecoratedBox(
        // ★ 壁纸：淡蓝→淡紫渐变（原来纯黑底 ⇒「黑漆麻糊」）
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFEAF3FF), Color(0xFFF6EDFF)],
          ),
        ),
        child: Column(children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
            color: const Color(0xFFFFFFFF),
            child: Row(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF2F6FEB),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('AI-OS',
                    style: TextStyle(fontSize: 12, color: Colors.white,
                                     fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text('$_name    $_status',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF6B7A90))),
              ),
            ]),
          ),
          Expanded(
            child: stack.isEmpty
                ? const Center(child: Text('还没有画布',
                    style: TextStyle(color: Color(0xFF6B7A90))))
                : Stack(children: stack),
          ),
        ]),
      ),
    );
  }
}


/// ★ 一层：谁（surface）、第几层（z）、摆哪（rect）、活没活（active）、内容（frame）。
/// ★ 全部【由呈现给】—— 渲染器不布局。
class _Layer {
  _Layer({
    required this.surface,
    required this.z,
    required this.rect,
    required this.active,
    required this.frame,
  });
  final String surface;
  final int z;
  final Rect? rect;
  final bool active;
  final Map<String, dynamic> frame;
}
