INCLUDE PERFETTO MODULE ext.loadline2_amazon_product;
INCLUDE PERFETTO MODULE ext.loadline2_cnn_article;
INCLUDE PERFETTO MODULE ext.loadline2_google_doc;
INCLUDE PERFETTO MODULE ext.loadline2_google_search_result;
INCLUDE PERFETTO MODULE ext.loadline2_youtube_video;

SELECT
  loadline2_amazon_product_score_visual() AS amazon_product_visual,
  loadline2_amazon_product_score_interactive() AS amazon_product_interactive,
  loadline2_cnn_article_score_visual() AS cnn_article_visual,
  loadline2_cnn_article_score_interactive() AS cnn_article_interactive,
  loadline2_google_doc_score_visual() AS google_doc_visual,
  loadline2_google_doc_score_interactive() AS google_doc_interactive,
  loadline2_google_search_result_score_visual() AS google_search_result_visual,
  loadline2_google_search_result_score_interactive() AS google_search_result_interactive,
  loadline2_youtube_video_score_visual() AS youtube_video_visual,
  loadline2_youtube_video_score_interactive() AS youtube_video_interactive;
